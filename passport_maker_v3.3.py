import sys
import os
from io import BytesIO

# GUI লাইব্রেরি
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QSpinBox, QFileDialog, 
                               QMessageBox, QFrame, QScrollArea, QProgressBar, 
                               QLineEdit, QColorDialog, QGraphicsDropShadowEffect, QSlider)
from PySide6.QtGui import QPixmap, QImage, QColor, QFont, QFontDatabase, QPainter
from PySide6.QtCore import Qt, QThread, Signal
# প্রিন্টিং লাইব্রেরি
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

# ইমেজ প্রসেসিং লাইব্রেরি
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from rembg import remove, new_session 

# --- ব্যাকগ্রাউন্ড রিমুভ করার থ্রেড ---
class BgRemoverThread(QThread):
    finished = Signal(object) 

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path

    def run(self):
        try:
            input_image = Image.open(self.image_path)
            session = new_session("u2net_human_seg")
            output_image = remove(
                input_image, 
                session=session,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=10
            )
            self.finished.emit(output_image)
        except Exception as e:
            print(f"Error in BG Removal: {e}")
            self.finished.emit(None)

class PassportMakerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("স্মার্ট পাসপোর্ট ফটো স্টুডিও V3 (Print Supported)")
        self.resize(1050, 780)
        
        # --- মডার্ন এবং সুন্দর ডিজাইন (CSS Style) ---
        self.setStyleSheet("""
            QWidget { 
                background-color: #f0f2f5; 
                font-family: 'BenSenHandwriting', 'Kalpurush', 'Nirmala UI', sans-serif;
                font-size: 15px;
            }
            QLabel { font-weight: bold; color: #374151; }
            QLabel#HeaderLabel {
                font-size: 24px; color: #1e3a8a; font-weight: 800;
            }
            QLabel#EnhanceLabel { color: #065f46; font-size: 14px;}
            
            QPushButton { 
                background-color: #ffffff; color: #1f2937; 
                border: 1px solid #d1d5db; border-radius: 8px; 
                padding: 10px 15px; font-weight: bold; text-align: left;
            }
            QPushButton:hover { background-color: #f3f4f6; border-color: #9ca3af; }
            QPushButton:disabled { background-color: #e5e7eb; color: #9ca3af; border-color: #e5e7eb; }
            
            QPushButton#PrimaryBtn { background-color: #2563eb; color: white; border: none; text-align: center; }
            QPushButton#PrimaryBtn:hover { background-color: #1d4ed8; }
            
            QPushButton#SuccessBtn { background-color: #059669; color: white; border: none; text-align: center; }
            QPushButton#SuccessBtn:hover { background-color: #047857; }

            QPushButton#DangerBtn { background-color: #dc2626; color: white; border: none; text-align: center; }
            QPushButton#DangerBtn:hover { background-color: #b91c1c; }
            
            /* নতুন প্রিন্ট বাটনের স্টাইল */
            QPushButton#PrintBtn { background-color: #7c3aed; color: white; border: none; text-align: center; }
            QPushButton#PrintBtn:hover { background-color: #6d28d9; }

            QLineEdit, QSpinBox { padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; background-color: white; }
            QLineEdit:focus { border: 1px solid #2563eb; }

            QFrame#Card { background-color: white; border-radius: 12px; border: 1px solid #e5e7eb; }
            
            QProgressBar { border: 1px solid #d1d5db; border-radius: 5px; text-align: center; background-color: white; }
            QProgressBar::chunk { background-color: #2563eb; }
            
            /* স্লাইডারের স্টাইল */
            QSlider::groove:horizontal { border: 1px solid #bbb; background: white; height: 8px; border-radius: 4px; }
            QSlider::sub-page:horizontal { background: #2563eb; border: 1px solid #777; height: 8px; border-radius: 4px; }
            QSlider::handle:horizontal { background: #ffffff; border: 2px solid #2563eb; width: 16px; margin-top: -5px; margin-bottom: -5px; border-radius: 8px; }
        """)

        # ভেরিয়েবল
        self.transparent_image = None  
        self.processed_passport_photo = None 
        self.a4_sheet = None

        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- বাম পাশ: কন্ট্রোল প্যানেল ---
        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_panel.setFixedWidth(360)
        
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
        header.setObjectName("HeaderLabel") 
        header.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(header)

        # ১. আপলোড
        left_layout.addWidget(QLabel("১. ছবি নির্বাচন"))
        self.btn_upload = QPushButton(" ছবি আপলোড করুন")
        self.btn_upload.setObjectName("PrimaryBtn") 
        self.btn_upload.setCursor(Qt.PointingHandCursor)
        self.btn_upload.clicked.connect(self.upload_image)
        left_layout.addWidget(self.btn_upload)

        # লোডিং
        self.loading_label = QLabel("প্রসেসিং হচ্ছে... ⏳\n(প্রথমবার একটু সময় লাগতে পারে)")
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

        # ৩. স্মার্ট এনহ্যান্স (Volume)
        self.lbl_enhance = QLabel("৩. ছবি ক্লিয়ার/শার্প করুন: Level 0 (Normal)")
        self.lbl_enhance.setObjectName("EnhanceLabel")
        left_layout.addWidget(self.lbl_enhance)
        
        self.slider_enhance = QSlider(Qt.Horizontal)
        self.slider_enhance.setRange(0, 10) # 0 থেকে 10 লেভেল
        self.slider_enhance.setValue(0)
        self.slider_enhance.setCursor(Qt.PointingHandCursor)
        self.slider_enhance.valueChanged.connect(self.on_slider_changed)
        left_layout.addWidget(self.slider_enhance)

        left_layout.addWidget(self.create_h_line())

        # ৪. কপি
        left_layout.addWidget(QLabel("৪. কত কপি ছবি লাগবে?"))
        self.spin_copies = QSpinBox()
        self.spin_copies.setRange(1, 30)
        self.spin_copies.setValue(4)
        left_layout.addWidget(self.spin_copies)

        left_layout.addStretch()

        # ৫. জেনারেট
        self.btn_generate = QPushButton(" ৫. A4 পেপার সাজান")
        self.btn_generate.setObjectName("SuccessBtn")
        self.btn_generate.setCursor(Qt.PointingHandCursor)
        self.btn_generate.clicked.connect(self.generate_a4_layout)
        self.btn_generate.setEnabled(False)
        left_layout.addWidget(self.btn_generate)

        # ৬. বাটন লেআউট (সেভ এবং প্রিন্ট)
        btn_action_layout = QHBoxLayout()
        
        self.btn_save = QPushButton(" সেভ করুন")
        self.btn_save.setObjectName("DangerBtn") 
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_for_print)
        self.btn_save.setEnabled(False)
        
        self.btn_print = QPushButton(" প্রিন্ট করুন")
        self.btn_print.setObjectName("PrintBtn") 
        self.btn_print.setCursor(Qt.PointingHandCursor)
        self.btn_print.clicked.connect(self.print_a4_sheet)
        self.btn_print.setEnabled(False)

        btn_action_layout.addWidget(self.btn_save)
        btn_action_layout.addWidget(self.btn_print)
        
        left_layout.addLayout(btn_action_layout)
        main_layout.addWidget(left_panel)

        # --- ডান পাশ: প্রিভিউ ---
        right_panel = QFrame()
        right_panel.setObjectName("Card")
        
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
            self.apply_changes() 
            QMessageBox.information(self, "সফল!", "ব্যাকগ্রাউন্ড রিমুভ হয়েছে! এখন আপনি কালার বা এনহ্যান্স পরিবর্তন করতে পারেন।")
        else:
            QMessageBox.critical(self, "ত্রুটি", "ছবি প্রসেস করা যায়নি।")

    def open_color_picker(self):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_code = color.name().upper()
            self.txt_hex.setText(hex_code)
            self.update_color_btn_icon(hex_code)

    def on_slider_changed(self, value):
        if value == 0:
            self.lbl_enhance.setText("৩. ছবি ক্লিয়ার/শার্প করুন: Level 0 (Normal)")
        else:
            self.lbl_enhance.setText(f"৩. ছবি ক্লিয়ার/শার্প করুন: Level {value}")
        self.apply_changes()

    def apply_changes(self):
        if not self.transparent_image: return

        try:
            # ১. কালার নেওয়া
            hex_color = self.txt_hex.text().strip()
            if not hex_color.startswith("#"): hex_color = "#" + hex_color
            self.update_color_btn_icon(hex_color) 

            try:
                Image.new("RGB", (1, 1), hex_color)
            except:
                hex_color = "#FFFFFF" 

            # ২. ব্যাকগ্রাউন্ড লেয়ার তৈরি
            fg_img = self.transparent_image.copy()
            bg_layer = Image.new("RGBA", fg_img.size, hex_color)
            
            # ৩. ছবি মার্জ করা
            bg_layer.paste(fg_img, (0, 0), fg_img)
            final_img = bg_layer.convert("RGB")

            # ৪. এনহ্যান্স (স্লাইডারের ভ্যালু অনুযায়ী)
            slider_val = self.slider_enhance.value()
            if slider_val > 0:
                # 0 লেভেলে Sharpness 1.0 (পরিবর্তন নাই), 10 লেভেলে 3.0
                sharpness_factor = 1.0 + (slider_val * 0.2) 
                contrast_factor = 1.0 + (slider_val * 0.02)

                enhancer = ImageEnhance.Sharpness(final_img)
                final_img = enhancer.enhance(sharpness_factor)
                enhancer_con = ImageEnhance.Contrast(final_img)
                final_img = enhancer_con.enhance(contrast_factor)

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
        self.btn_print.setEnabled(True) # প্রিন্ট বাটন একটিভ করা হলো

    def show_preview(self, pil_image, label, h):
        im_data = BytesIO()
        pil_image.save(im_data, "PNG")
        qimg = QImage.fromData(im_data.getvalue())
        pixmap = QPixmap.fromImage(qimg)
        label.setPixmap(pixmap.scaledToHeight(h, Qt.SmoothTransformation))

    def save_for_print(self):
        if self.a4_sheet:
            f, _ = QFileDialog.getSaveFileName(self, "Save", "passport_print.jpg", "JPG (*.jpg);;PDF (*.pdf)")
            if f:
                self.a4_sheet.save(f, resolution=300)
                QMessageBox.information(self, "সফল!", "ফাইল সেভ হয়েছে! এখন আপনি প্রিন্ট করতে পারেন।")

    # --- সরাসরি প্রিন্ট করার ফাংশন ---
    def print_a4_sheet(self):
        if not self.a4_sheet: return

        # PIL Image থেকে QImage এ কনভার্ট
        im_data = BytesIO()
        self.a4_sheet.save(im_data, "PNG")
        qimage = QImage.fromData(im_data.getvalue())

        # প্রিন্টার সেটআপ
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            # প্রিন্টারের পেজের সাইজ অনুযায়ী ছবি ফিট করানো
            rect = painter.viewport()
            size = qimage.size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(qimage.rect())
            painter.drawImage(0, 0, qimage)
            painter.end()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PassportMakerApp()
    window.show()
    sys.exit(app.exec())