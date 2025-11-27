import sys
import os
from io import BytesIO

# GUI লাইব্রেরি
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QSpinBox, QFileDialog, 
                               QMessageBox, QFrame, QScrollArea, QProgressBar, 
                               QCheckBox, QLineEdit, QColorDialog, QGraphicsDropShadowEffect)
from PySide6.QtGui import QPixmap, QImage, QColor, QFont, QFontDatabase
from PySide6.QtCore import Qt, QThread, Signal

# ইমেজ প্রসেসিং লাইব্রেরি
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from rembg import remove

# --- ব্যাকগ্রাউন্ড রিমুভ করার থ্রেড (শুধুমাত্র রিমুভ করবে) ---
class BgRemoverThread(QThread):
    finished = Signal(object) 

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path

    def run(self):
        try:
            input_image = Image.open(self.image_path)
            # শুধু ব্যাকগ্রাউন্ড রিমুভ করে ট্রান্সপারেন্ট ইমেজ ফেরত দিবে
            output_image = remove(input_image)
            self.finished.emit(output_image)
        except Exception as e:
            self.finished.emit(None)

class PassportMakerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("স্মার্ট পাসপোর্ট ফটো স্টুডিও V2")
        self.resize(1000, 750)
        
        # --- মডার্ন এবং সুন্দর ডিজাইন (CSS Style) ---
        # ফন্ট ফ্যামিলি আপডেট করা হয়েছে: SolaimanLipi এবং Kalpurush কে প্রাধান্য দেওয়া হয়েছে
        self.setStyleSheet("""
            QWidget { 
                background-color: #f0f2f5; 
                font-family: 'SolaimanLipi', 'Kalpurush', 'Nirmala UI', 'Siyam Rupali', Arial, sans-serif;
                font-size: 15px;
            }
            QLabel { 
                font-weight: bold; 
                color: #374151; 
            }
            /* হেডার টাইটেলের জন্য আলাদা স্টাইল */
            QLabel#HeaderLabel {
                font-family: 'SolaimanLipi', 'Kalpurush', serif;
                font-size: 24px;
                color: #1e3a8a;
                font-weight: 800;
            }
            QPushButton { 
                background-color: #ffffff; 
                color: #1f2937; 
                border: 1px solid #d1d5db; 
                border-radius: 8px; 
                padding: 10px 15px; 
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover { 
                background-color: #f3f4f6; 
                border-color: #9ca3af;
            }
            QPushButton:disabled { 
                background-color: #e5e7eb; 
                color: #9ca3af;
                border-color: #e5e7eb;
            }
            /* প্রাইমারি বাটন স্টাইল (নীল) */
            QPushButton#PrimaryBtn {
                background-color: #2563eb; 
                color: white; 
                border: none;
                text-align: center;
            }
            QPushButton#PrimaryBtn:hover { background-color: #1d4ed8; }
            
            /* সাকসেস বাটন স্টাইল (সবুজ) */
            QPushButton#SuccessBtn {
                background-color: #059669; 
                color: white; 
                border: none;
                text-align: center;
            }
            QPushButton#SuccessBtn:hover { background-color: #047857; }

            /* ডেঞ্জার বাটন স্টাইল (লাল) */
            QPushButton#DangerBtn {
                background-color: #dc2626; 
                color: white; 
                border: none;
                text-align: center;
            }
            QPushButton#DangerBtn:hover { background-color: #b91c1c; }

            QLineEdit { 
                padding: 8px; 
                border: 1px solid #d1d5db; 
                border-radius: 6px; 
                background-color: white;
            }
            QLineEdit:focus { border: 1px solid #2563eb; }

            QSpinBox {
                padding: 8px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: white;
            }

            QFrame#Card { 
                background-color: white; 
                border-radius: 12px; 
                border: 1px solid #e5e7eb; 
            }
            QCheckBox { spacing: 8px; font-weight: bold; color: #065f46; }
            QCheckBox::indicator { width: 18px; height: 18px; }
            QProgressBar {
                border: 1px solid #d1d5db;
                border-radius: 5px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk { background-color: #2563eb; }
        """)

        # ভেরিয়েবল
        self.transparent_image = None       # অরিজিনাল ব্যাকগ্রাউন্ড ছাড়া ছবি
        self.processed_passport_photo = None # কালার ও বর্ডার সহ ফাইনাল ছবি
        self.a4_sheet = None

        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- বাম পাশ: কন্ট্রোল প্যানেল ---
        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_panel.setFixedWidth(350)
        
        # শ্যাডো ইফেক্ট
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 0)
        left_panel.setGraphicsEffect(shadow)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(20, 20, 20, 20)

        # হেডার
        header = QLabel("পাসপোর্ট টুলবক্স")
        header.setObjectName("HeaderLabel") # আলাদা স্টাইল অ্যাপ্লাই হবে
        header.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(header)

        # ১. আপলোড
        upload_label = QLabel("১. ছবি নির্বাচন")
        left_layout.addWidget(upload_label)
        
        self.btn_upload = QPushButton(" ছবি আপলোড করুন")
        self.btn_upload.setIcon(QPixmap(16, 16)) # আইকনের জায়গা
        self.btn_upload.setObjectName("PrimaryBtn") # নীল করে দিলাম যাতে সুন্দর লাগে
        self.btn_upload.setCursor(Qt.PointingHandCursor)
        self.btn_upload.clicked.connect(self.upload_image)
        left_layout.addWidget(self.btn_upload)

        # এনহ্যান্স অপশন
        self.chk_enhance = QCheckBox("ছবি ক্লিয়ার/শার্প করুন (Smart Enhance)")
        self.chk_enhance.setChecked(True)
        self.chk_enhance.setCursor(Qt.PointingHandCursor)
        self.chk_enhance.stateChanged.connect(self.apply_changes)
        left_layout.addWidget(self.chk_enhance)

        # লোডিং
        self.loading_label = QLabel("প্রসেসিং হচ্ছে... ⏳")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #d97706; font-size: 13px; font-weight: normal;")
        self.loading_label.setVisible(False)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        left_layout.addWidget(self.loading_label)
        left_layout.addWidget(self.progress)
        
        left_layout.addWidget(self.create_h_line())

        # ২. ব্যাকগ্রাউন্ড কালার
        left_layout.addWidget(QLabel("২. ব্যাকগ্রাউন্ড কালার"))
        
        color_row = QHBoxLayout()
        self.txt_hex = QLineEdit("#FFFFFF") 
        self.txt_hex.setPlaceholderText("#RRGGBB")
        self.txt_hex.textChanged.connect(self.apply_changes)
        
        self.btn_color_picker = QPushButton("")
        self.btn_color_picker.setStyleSheet("background-color: #e5e7eb; border: 1px solid #ccc;")
        self.btn_color_picker.setFixedWidth(40)
        self.btn_color_picker.setCursor(Qt.PointingHandCursor)
        self.update_color_btn_icon("#FFFFFF")
        self.btn_color_picker.clicked.connect(self.open_color_picker)
        
        color_row.addWidget(self.txt_hex)
        color_row.addWidget(self.btn_color_picker)
        left_layout.addLayout(color_row)

        left_layout.addWidget(self.create_h_line())

        # ৩. কপি
        left_layout.addWidget(QLabel("৩. কত কপি ছবি লাগবে?"))
        self.spin_copies = QSpinBox()
        self.spin_copies.setRange(1, 30)
        self.spin_copies.setValue(4)
        left_layout.addWidget(self.spin_copies)

        left_layout.addStretch()

        # ৪. জেনারেট
        self.btn_generate = QPushButton(" ৩. A4 পেপার সাজান")
        self.btn_generate.setObjectName("SuccessBtn")
        self.btn_generate.setCursor(Qt.PointingHandCursor)
        self.btn_generate.clicked.connect(self.generate_a4_layout)
        self.btn_generate.setEnabled(False)
        left_layout.addWidget(self.btn_generate)

        # ৫. সেভ
        self.btn_save = QPushButton(" ৪. প্রিন্টের জন্য সেভ করুন")
        self.btn_save.setObjectName("DangerBtn") 
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_for_print)
        self.btn_save.setEnabled(False)
        left_layout.addWidget(self.btn_save)

        main_layout.addWidget(left_panel)

        # --- ডান পাশ: প্রিভিউ ---
        right_panel = QFrame()
        right_panel.setObjectName("Card")
        
        # শ্যাডো
        shadow2 = QGraphicsDropShadowEffect()
        shadow2.setBlurRadius(15)
        shadow2.setColor(QColor(0, 0, 0, 20))
        shadow2.setOffset(0, 0)
        right_panel.setGraphicsEffect(shadow2)

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)

        # সিঙ্গেল
        right_layout.addWidget(QLabel("সিঙ্গেল প্রিভিউ"))
        
        preview_container = QFrame()
        preview_container.setStyleSheet("background-color: #f9fafb; border: 1px dashed #d1d5db; border-radius: 8px;")
        preview_layout = QVBoxLayout(preview_container)
        
        self.lbl_single_preview = QLabel("কোনো ছবি নেই")
        self.lbl_single_preview.setAlignment(Qt.AlignCenter)
        self.lbl_single_preview.setStyleSheet("color: #9ca3af; font-weight: normal;")
        self.lbl_single_preview.setMinimumHeight(220)
        
        preview_layout.addWidget(self.lbl_single_preview)
        right_layout.addWidget(preview_container)

        # A4
        right_layout.addWidget(QLabel("A4 পেপার প্রিভিউ"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #e5e7eb; border-radius: 8px; }")
        
        self.lbl_a4_preview = QLabel()
        self.lbl_a4_preview.setAlignment(Qt.AlignCenter)
        self.lbl_a4_preview.setStyleSheet("background-color: #e5e7eb;")
        scroll.setWidget(self.lbl_a4_preview)
        
        right_layout.addWidget(scroll)

        main_layout.addWidget(right_panel)

    def create_h_line(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #e5e7eb;")
        return line

    def update_color_btn_icon(self, hex_color):
        # বাটনের কালার আপডেট করা
        self.btn_color_picker.setStyleSheet(f"""
            background-color: {hex_color}; 
            border: 1px solid #9ca3af; 
            border-radius: 4px;
        """)

    # --- লজিক ---

    def upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "ছবি নিন", "", "Images (*.jpg *.png *.jpeg)")
        if file_path:
            self.btn_upload.setEnabled(False)
            self.loading_label.setVisible(True)
            self.progress.setVisible(True)
            self.progress.setRange(0, 0)
            
            self.bg_thread = BgRemoverThread(file_path)
            self.bg_thread.finished.connect(self.on_bg_removed_finish)
            self.bg_thread.start()

    def on_bg_removed_finish(self, img_obj):
        self.btn_upload.setEnabled(True)
        self.loading_label.setVisible(False)
        self.progress.setVisible(False)

        if img_obj:
            self.transparent_image = img_obj
            self.apply_changes() # ব্যাকগ্রাউন্ড রিমুভ হলে কালার অ্যাপ্লাই কর
            QMessageBox.information(self, "সফল!", "ব্যাকগ্রাউন্ড রিমুভ হয়েছে! এখন আপনি কালার পরিবর্তন করতে পারেন।")
        else:
            QMessageBox.critical(self, "ত্রুটি", "ছবি প্রসেস করা যায়নি।")

    def open_color_picker(self):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_code = color.name().upper()
            self.txt_hex.setText(hex_code)
            self.update_color_btn_icon(hex_code)

    def apply_changes(self):
        # যদি মেইন ছবি না থাকে, কিছু করার দরকার নেই
        if not self.transparent_image: return

        try:
            # ১. কালার নেওয়া
            hex_color = self.txt_hex.text().strip()
            if not hex_color.startswith("#"): hex_color = "#" + hex_color
            
            self.update_color_btn_icon(hex_color) # বাটন কালার আপডেট

            # ভ্যালিডেশন: ভুল কালার দিলে সাদা হয়ে যাবে
            try:
                Image.new("RGB", (1, 1), hex_color)
            except:
                hex_color = "#FFFFFF" 

            # ২. ব্যাকগ্রাউন্ড লেয়ার তৈরি
            fg_img = self.transparent_image.copy()
            bg_layer = Image.new("RGBA", fg_img.size, hex_color)
            
            # ৩. ছবি মার্জ করা
            bg_layer.paste(fg_img, (0, 0), fg_img)
            final_img = bg_layer.convert("RGB")

            # ৪. এনহ্যান্স (যদি টিক দেওয়া থাকে)
            if self.chk_enhance.isChecked():
                enhancer = ImageEnhance.Sharpness(final_img)
                final_img = enhancer.enhance(1.8)
                enhancer_con = ImageEnhance.Contrast(final_img)
                final_img = enhancer_con.enhance(1.1)

            # ৫. রিসাইজ (পাসপোর্ট সাইজ)
            target_size = (450, 570)
            final_img = ImageOps.fit(final_img, target_size, Image.Resampling.LANCZOS)

            # ৬. বর্ডার
            final_img = ImageOps.expand(final_img, border=3, fill='#808080')

            self.processed_passport_photo = final_img
            
            # প্রিভিউ আপডেট
            self.show_preview(self.processed_passport_photo, self.lbl_single_preview, 250)
            self.btn_generate.setEnabled(True)

        except Exception as e:
            print(f"Error applying changes: {e}")

    def generate_a4_layout(self):
        if not self.processed_passport_photo: return

        copies = self.spin_copies.value()
        a4_w, a4_h = 2480, 3508
        a4_canvas = Image.new("RGB", (a4_w, a4_h), "white")
        
        img_w, img_h = self.processed_passport_photo.size
        x, y = 100, 100
        gap = 50

        for _ in range(copies):
            a4_canvas.paste(self.processed_passport_photo, (x, y))
            x += img_w + gap
            if x + img_w > a4_w:
                x = 100
                y += img_h + gap

        self.a4_sheet = a4_canvas
        self.show_preview(self.a4_sheet, self.lbl_a4_preview, 400)
        self.btn_save.setEnabled(True)

    def show_preview(self, pil_image, label, h):
        im_data = BytesIO()
        pil_image.save(im_data, "PNG")
        qimg = QImage.fromData(im_data.getvalue())
        pixmap = QPixmap.fromImage(qimg)
        label.setPixmap(pixmap.scaledToHeight(h, Qt.SmoothTransformation))

    def save_for_print(self):
        if self.a4_sheet:
            f, _ = QFileDialog.getSaveFileName(self, "Save", "passport_print.pdf", "PDF (*.pdf);;JPG (*.jpg)")
            if f:
                self.a4_sheet.save(f, resolution=300)
                QMessageBox.information(self, "সফল!", "ফাইল সেভ হয়েছে! এখন আপনি প্রিন্ট করতে পারেন।")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PassportMakerApp()
    window.show()
    sys.exit(app.exec())