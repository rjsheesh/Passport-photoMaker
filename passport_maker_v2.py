import sys
import os
from io import BytesIO

# GUI লাইব্রেরি
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QSpinBox, QFileDialog, 
                               QMessageBox, QFrame, QScrollArea, QProgressBar, QCheckBox)
from PySide6.QtGui import QPixmap, QImage, QFont
from PySide6.QtCore import Qt, QThread, Signal

# ইমেজ প্রসেসিং লাইব্রেরি
from PIL import Image, ImageOps, ImageDraw, ImageEnhance, ImageFilter
from rembg import remove

# --- ব্যাকগ্রাউন্ড রিমুভ এবং এনহ্যান্স করার থ্রেড ---
class BgRemoverThread(QThread):
    finished = Signal(object) # সিগন্যাল যা প্রসেস করা ইমেজ মেইন থ্রেডে পাঠাবে

    def __init__(self, image_path, enhance_mode=False):
        super().__init__()
        self.image_path = image_path
        self.enhance_mode = enhance_mode

    def run(self):
        try:
            # ১. ইমেজ ওপেন করা
            input_image = Image.open(self.image_path)
            
            # ২. ব্যাকগ্রাউন্ড রিমুভ (rembg)
            output_image = remove(input_image)
            
            # ৩. সাদা ব্যাকগ্রাউন্ড লেয়ার যোগ করা
            white_bg = Image.new("RGBA", output_image.size, "WHITE")
            white_bg.paste(output_image, (0, 0), output_image)
            final_image = white_bg.convert("RGB")
            
            # ৪. স্মার্ট এনহ্যান্সমেন্ট (যদি ইউজার চায়)
            if self.enhance_mode:
                # শার্পনেস বাড়ানো (ব্লার কমানোর জন্য)
                enhancer_sharp = ImageEnhance.Sharpness(final_image)
                final_image = enhancer_sharp.enhance(2.0) # ২ গুণ শার্প
                
                # কন্ট্রাস্ট একটু বাড়ানো (ছবি উজ্জ্বল করতে)
                enhancer_contrast = ImageEnhance.Contrast(final_image)
                final_image = enhancer_contrast.enhance(1.1)
                
                # কালার একটু পপ করা
                enhancer_color = ImageEnhance.Color(final_image)
                final_image = enhancer_color.enhance(1.1)
                
                # ডিটেইল ফিল্টার (অপশনাল)
                final_image = final_image.filter(ImageFilter.DETAIL)

            self.finished.emit(final_image)
        except Exception as e:
            self.finished.emit(None)

class PassportMakerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("স্মার্ট পাসপোর্ট ফটো মেকার")
        self.resize(900, 700)
        
        # স্টাইলশিট
        self.setStyleSheet("""
            QWidget { background-color: #f3f4f6; font-family: Arial; }
            QLabel { font-weight: bold; color: #333; }
            QPushButton { 
                background-color: #2563eb; color: white; border-radius: 5px; 
                padding: 10px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:disabled { background-color: #9ca3af; }
            QSpinBox { padding: 5px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; }
            QFrame#Card { background-color: white; border-radius: 10px; border: 1px solid #e5e7eb; }
            QCheckBox { font-weight: bold; color: #065f46; font-size: 13px; }
        """)

        # ভেরিয়েবল
        self.processed_passport_photo = None # প্রসেস করা সিঙ্গেল ছবি
        self.a4_sheet = None # প্রিন্টের জন্য তৈরি পেজ

        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)

        # --- বাম পাশ: কন্ট্রোল প্যানেল ---
        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15)

        # হেডার
        header = QLabel("পাসপোর্ট টুলবক্স")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 18px; color: #1e3a8a; margin-bottom: 10px;")
        left_layout.addWidget(header)

        # ১. ছবি আপলোড বাটন
        self.btn_upload = QPushButton("১. ছবি আপলোড করুন")
        self.btn_upload.clicked.connect(self.upload_image)
        left_layout.addWidget(self.btn_upload)
        
        # এনহ্যান্স চেকবক্স (নতুন ফিচার)
        self.chk_enhance = QCheckBox("ছবি ক্লিয়ার/শার্প করুন (Smart Enhance)")
        self.chk_enhance.setChecked(True) # ডিফল্টভাবে অন থাকবে
        self.chk_enhance.setToolTip("ছবি যদি ঘোলা বা ব্লার থাকে, তবে এটি টিক দিন।")
        left_layout.addWidget(self.chk_enhance)

        # লোডিং বার (লুকানো থাকবে)
        self.loading_label = QLabel("কাজ চলছে... একটু সময় দিন ⏳")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #d97706; font-size: 12px;")
        self.loading_label.setVisible(False)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # Infinite loop style
        self.progress.setVisible(False)
        left_layout.addWidget(self.loading_label)
        left_layout.addWidget(self.progress)

        # ২. কপি সংখ্যা ইনপুট
        left_layout.addWidget(QLabel("২. কত কপি ছবি লাগবে?"))
        self.spin_copies = QSpinBox()
        self.spin_copies.setRange(1, 30)
        self.spin_copies.setValue(4) # ডিফল্ট ৪ কপি
        left_layout.addWidget(self.spin_copies)

        # ৩. জেনারেট বাটন
        self.btn_generate = QPushButton("৩. A4 পেপার সাজান")
        self.btn_generate.setStyleSheet("background-color: #059669;")
        self.btn_generate.clicked.connect(self.generate_a4_layout)
        self.btn_generate.setEnabled(False)
        left_layout.addWidget(self.btn_generate)

        # ৪. সেভ বাটন
        self.btn_save = QPushButton("৪. প্রিন্টের জন্য সেভ করুন")
        self.btn_save.setStyleSheet("background-color: #dc2626;")
        self.btn_save.clicked.connect(self.save_for_print)
        self.btn_save.setEnabled(False)
        left_layout.addWidget(self.btn_save)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # --- ডান পাশ: প্রিভিউ এরিয়া ---
        right_panel = QFrame()
        right_panel.setObjectName("Card")
        right_layout = QVBoxLayout(right_panel)

        # সিঙ্গেল ফটো প্রিভিউ
        right_layout.addWidget(QLabel("সিঙ্গেল পাসপোর্ট সাইজ প্রিভিউ:"))
        self.lbl_single_preview = QLabel()
        self.lbl_single_preview.setAlignment(Qt.AlignCenter)
        self.lbl_single_preview.setStyleSheet("border: 1px dashed #ccc; min-height: 200px;")
        right_layout.addWidget(self.lbl_single_preview)

        # A4 লেআউট প্রিভিউ
        right_layout.addWidget(QLabel("A4 পেপার প্রিভিউ:"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.lbl_a4_preview = QLabel()
        self.lbl_a4_preview.setAlignment(Qt.AlignCenter)
        self.lbl_a4_preview.setStyleSheet("background-color: #ddd;")
        scroll.setWidget(self.lbl_a4_preview)
        
        right_layout.addWidget(scroll)
        main_layout.addWidget(right_panel)

    # --- লজিক সেকশন ---

    def upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "ছবি সিলেক্ট করুন", "", "Images (*.jpg *.jpeg *.png)")
        
        if file_path:
            # UI আপডেট (লোডিং শুরু)
            self.btn_upload.setEnabled(False)
            self.loading_label.setVisible(True)
            self.progress.setVisible(True)
            
            # ইউজার এনহ্যান্স চায় কিনা চেক করা
            should_enhance = self.chk_enhance.isChecked()
            
            # ব্যাকগ্রাউন্ড থ্রেড চালু
            self.bg_thread = BgRemoverThread(file_path, enhance_mode=should_enhance)
            self.bg_thread.finished.connect(self.on_bg_removed)
            self.bg_thread.start()

    def on_bg_removed(self, img_obj):
        # লোডিং বন্ধ
        self.btn_upload.setEnabled(True)
        self.loading_label.setVisible(False)
        self.progress.setVisible(False)

        if img_obj is None:
            QMessageBox.critical(self, "Error", "ছবি প্রসেস করা যায়নি। দয়া করে অন্য ছবি চেষ্টা করুন।")
            return

        # ১. পাসপোর্ট সাইজ রিসাইজ (1.5 inch x 1.9 inch @ 300 DPI)
        # 1.5 inch * 300 dpi = 450 pixels
        # 1.9 inch * 300 dpi = 570 pixels
        target_size = (450, 570)
        
        # ImageOps.fit ব্যবহার করলে ছবি চ্যাপ্টা হবে না, মাঝখান থেকে ক্রপ করে সাইজ করবে
        passport_img = ImageOps.fit(img_obj, target_size, Image.Resampling.LANCZOS)

        # ২. বর্ডার যোগ করা (3px Grey)
        # বর্ডার যোগ করার জন্য মূল সাইজ থেকে একটু কমিয়ে বর্ডার দিতে হবে যাতে ফাইনাল সাইজ ঠিক থাকে
        # অথবা বাইরে বর্ডার দিতে পারি। এখানে আমরা বাইরে বর্ডার দিচ্ছি।
        passport_with_border = ImageOps.expand(passport_img, border=3, fill='#808080') # Grey Border

        self.processed_passport_photo = passport_with_border
        
        # প্রিভিউ দেখানো
        self.show_preview(self.processed_passport_photo, self.lbl_single_preview, scale_h=250)
        self.btn_generate.setEnabled(True)
        
        msg = "ব্যাকগ্রাউন্ড রিমুভ ও সাইজ ঠিক করা হয়েছে!"
        if self.chk_enhance.isChecked():
            msg += "\n(স্মার্ট এনহ্যান্সমেন্ট প্রয়োগ করা হয়েছে)"
        QMessageBox.information(self, "Success", msg)

    def generate_a4_layout(self):
        if not self.processed_passport_photo: return

        copies = self.spin_copies.value()
        
        # A4 সাইজ পিক্সেল এ (300 DPI) -> 2480 x 3508 pixels
        a4_width = 2480
        a4_height = 3508
        a4_canvas = Image.new("RGB", (a4_width, a4_height), "white")
        
        img_w, img_h = self.processed_passport_photo.size
        
        # মার্জিন এবং গ্যাপ
        start_x = 100
        start_y = 100
        gap_x = 50
        gap_y = 100

        current_x = start_x
        current_y = start_y

        for i in range(copies):
            # পেস্ট করা
            a4_canvas.paste(self.processed_passport_photo, (current_x, current_y))
            
            # পরের পজিশন ক্যালকুলেট করা
            current_x += img_w + gap_x
            
            # যদি ডান পাশে জায়গা না থাকে, নিচে নামো
            if current_x + img_w > a4_width:
                current_x = start_x
                current_y += img_h + gap_y

        self.a4_sheet = a4_canvas
        
        # A4 প্রিভিউ দেখানো (অনেক ছোট করে, নাহলে স্ক্রিনে ধরবে না)
        self.show_preview(self.a4_sheet, self.lbl_a4_preview, scale_h=400)
        self.btn_save.setEnabled(True)

    def show_preview(self, pil_image, label_widget, scale_h):
        # PIL ইমেজকে QPixmap এ কনভার্ট করে লেবেলে দেখানো
        im_data = BytesIO()
        pil_image.save(im_data, "PNG")
        qimg = QImage.fromData(im_data.getvalue())
        pixmap = QPixmap.fromImage(qimg)
        
        # রিসাইজ প্রিভিউ এর জন্য
        scaled_pixmap = pixmap.scaledToHeight(scale_h, Qt.SmoothTransformation)
        label_widget.setPixmap(scaled_pixmap)

    def save_for_print(self):
        if self.a4_sheet:
            # ফাইল সেভ করার অপশন (PDF ডিফল্ট)
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "সেভ করুন", 
                "passport_print.pdf", 
                "PDF Document (*.pdf);;JPEG Image (*.jpg);;PNG Image (*.png)"
            )
            
            if file_path:
                # PDF বা ইমেজ হিসেবে সেভ করা
                # resolution=300 দিলে প্রিন্ট কোয়ালিটি ভালো থাকে
                self.a4_sheet.save(file_path, resolution=300)
                QMessageBox.information(self, "Done", "ফাইল সেভ হয়েছে! \nএখন এটি ওপেন করে প্রিন্ট (Ctrl+P) দিন।")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PassportMakerApp()
    window.show()
    sys.exit(app.exec())