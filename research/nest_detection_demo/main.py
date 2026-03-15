# -*- coding: utf-8 -*-
import os
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QFileDialog, QLabel, QApplication
import image_rc
import threading
import cv2
import numpy as np
import time
from Yolo11Detector import *


class Ui_MainWindow(QtWidgets.QMainWindow):
    signal = QtCore.pyqtSignal(str, str)

    def setupUi(self):
        self.setObjectName("MainWindow")
        self.resize(1280, 728)
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.detector=None
        self.weights_dir = './weights'

        self.picture = QtWidgets.QLabel(self.centralwidget)
        self.picture.setGeometry(QtCore.QRect(260, 10, 1010, 630))
        self.picture.setStyleSheet("background:black")
        self.picture.setObjectName("picture")
        self.picture.setScaledContents(True)
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(10, 10, 81, 21))
        self.label_2.setObjectName("label_2")
        self.cb_weights = QtWidgets.QComboBox(self.centralwidget)
        self.cb_weights.setGeometry(QtCore.QRect(10, 40, 241, 21))
        self.cb_weights.setObjectName("cb_weights")
        self.cb_weights.currentIndexChanged.connect(self.cb_weights_changed)

        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(10, 70, 72, 21))
        self.label_3.setObjectName("label_3")
        self.hs_conf = QtWidgets.QSlider(self.centralwidget)
        self.hs_conf.setGeometry(QtCore.QRect(10, 100, 181, 22))
        self.hs_conf.setProperty("value", 25)
        self.hs_conf.setOrientation(QtCore.Qt.Horizontal)
        self.hs_conf.setObjectName("hs_conf")
        self.hs_conf.valueChanged.connect(self.conf_change)
        self.dsb_conf = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.dsb_conf.setGeometry(QtCore.QRect(200, 100, 51, 22))
        self.dsb_conf.setMaximum(1.0)
        self.dsb_conf.setSingleStep(0.01)
        self.dsb_conf.setProperty("value", 0.3)
        self.dsb_conf.setObjectName("dsb_conf")
        self.dsb_conf.valueChanged.connect(self.dsb_conf_change)
        self.dsb_iou = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.dsb_iou.setGeometry(QtCore.QRect(200, 160, 51, 22))
        self.dsb_iou.setMaximum(1.0)
        self.dsb_iou.setSingleStep(0.01)
        self.dsb_iou.setProperty("value", 0.45)
        self.dsb_iou.setObjectName("dsb_iou")
        self.dsb_iou.valueChanged.connect(self.dsb_iou_change)
        self.hs_iou = QtWidgets.QSlider(self.centralwidget)
        self.hs_iou.setGeometry(QtCore.QRect(10, 160, 181, 22))
        self.hs_iou.setProperty("value", 45)
        self.hs_iou.setOrientation(QtCore.Qt.Horizontal)
        self.hs_iou.setObjectName("hs_iou")
        self.hs_iou.valueChanged.connect(self.iou_change)
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setGeometry(QtCore.QRect(10, 130, 72, 21))
        self.label_4.setObjectName("label_4")
        self.label_5 = QtWidgets.QLabel(self.centralwidget)
        self.label_5.setGeometry(QtCore.QRect(10, 210, 72, 21))
        self.label_5.setObjectName("label_5")
        self.le_res = QtWidgets.QTextEdit(self.centralwidget)
        self.le_res.setGeometry(QtCore.QRect(10, 240, 241, 400))
        self.le_res.setObjectName("le_res")
        self.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1110, 30))
        self.menubar.setObjectName("menubar")
        self.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)
        self.toolBar = QtWidgets.QToolBar(self)
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toolBar.setObjectName("toolBar")
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.actionopenpic = QtWidgets.QAction(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/images/1.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionopenpic.setIcon(icon)
        self.actionopenpic.setObjectName("actionopenpic")
        self.actionopenpic.triggered.connect(self.open_image)
        self.action = QtWidgets.QAction(self)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/images/2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.action.setIcon(icon1)
        self.action.setObjectName("action")
        self.action.triggered.connect(self.open_video)
        self.action_2 = QtWidgets.QAction(self)
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/images/3.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.action_2.setIcon(icon2)
        self.action_2.setObjectName("action_2")
        self.action_2.triggered.connect(self.open_camera)

        self.actionexit = QtWidgets.QAction(self)
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":/images/4.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionexit.setIcon(icon3)
        self.actionexit.setObjectName("actionexit")
        self.actionexit.triggered.connect(self.exit)

        self.toolBar.addAction(self.actionopenpic)
        self.toolBar.addAction(self.action)
        self.toolBar.addAction(self.action_2)
        self.toolBar.addAction(self.actionexit)

        self.retranslateUi()
        QtCore.QMetaObject.connectSlotsByName(self)
        self.init_all()

    def exit(self):
        if self.camera_open:
            self.camera_open = False
            time.sleep(0.2)
        app = QApplication.instance()
        app.quit()

    def cb_weights_changed(self):
        title = self.windowTitle()
        self.setWindowTitle('正在加载模型中..')
        self.detector = Yolo11Detector(weights=os.path.join(self.weights_dir, self.cb_weights.currentText()))
        self.setWindowTitle(title)

    def open_camera(self):
        if self.action_2.text() == '打开摄像头':
            self.action_2.setText('停止')
            th = threading.Thread(target=self.start_camera)
            th.start()
        else:
            self.action_2.setText('打开摄像头')
            self.camera_open = False

    def set_res(self, res, flag):
        if flag == 'res':
            self.le_res.setPlainText(res)
        else:
            self.ssl_show.setText(res)

    def init_all(self):
        self.signal.connect(self.set_res)
        self.image_path = None
        self.camera_open = False
        self.load_weights_to_list()
        # 初始化状态栏
        self.initStatusBar()
        #print('正在加载模型...')
        #self.detector =Yolo11Detector(weights=os.path.join(self.weights_dir, self.cb_weights.itemText(0)))

    def resizeEvent(self, event):
        self.le_res.setFixedHeight(self.height() - self.le_res.y() - self.statusbar.height() - 40)
        self.picture.setFixedSize(self.width() - self.le_res.x() - self.le_res.width() - 20,
                                  self.height() - self.statusbar.height())

    def initStatusBar(self):
        # 定义文本标签
        self.statusLabel = QLabel()
        self.statusLabel.setText("状态说明   ")
        self.statusLabel.setObjectName('statusLabel')

        self.ssl_show = QLabel()
        self.ssl_show.setText("等待操作中...")
        self.ssl_show.setFixedSize(600, 32)
        self.ssl_show.setObjectName('statusLabel_show')

        # 往状态栏中添加组件（stretch应该是拉伸组件宽度）-->会添加到状态栏左侧
        self.statusbar.addWidget(self.statusLabel)
        self.statusbar.addWidget(self.ssl_show)

    def open_video(self):
        if self.action.text() == '选择视频':
            fileName, fileType = QtWidgets.QFileDialog.getOpenFileName(self, "选取文件", os.getcwd(),
                                                                       "Video File(*.mp4 *.avi *.flv)")
            if fileName == '':
                return
            self.action.setText('停止')
            th = threading.Thread(target=self.start_video, args=(fileName,))
            th.start()
        else:
            self.action.setText('选择视频')
            self.camera_open = False

    def start_camera(self, camera_index=0):
        self.signal.emit('正在检测摄像头中...','camera')
        cap = cv2.VideoCapture(camera_index)
        self.camera_open = True
        while self.camera_open:
            ret, frame = cap.read()
            if not ret:
                self.action_2.setText('打开摄像头')
                self.camera_open = False
                self.signal.emit('摄像头检测已停止!', 'camera')
                break
            result_lists = self.detector.inference_image(frame, False, self.dsb_conf.value(), self.dsb_iou.value())
            frame = self.detector.draw_image(result_lists, frame)
            res = self.get_result_str(result_lists)
            self.signal.emit(res, 'res')
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            img = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            self.picture.setPixmap(QPixmap.fromImage(img))
            time.sleep(0.001)
        cap.release()
        self.action_2.setText('打开摄像头')
        self.camera_open = False
        self.signal.emit('摄像头检测已停止!', 'camera')
        self.picture.setPixmap(QPixmap(""))

    def start_video(self, video_file):
        self.signal.emit('正在检测视频中...', 'video')
        cap = cv2.VideoCapture(video_file)
        self.camera_open = True
        while self.camera_open:
            ret, frame = cap.read()
            if not ret:
                self.action_2.setText('选择视频')
                self.camera_open = False
                self.signal.emit('视频检测已停止!', 'video')
                break

            result_lists = self.detector.inference_image(frame, False, self.dsb_conf.value(), self.dsb_iou.value())
            frame = self.detector.draw_image(result_lists, frame)
            res = self.get_result_str(result_lists)
            self.signal.emit(res,'res')
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            img = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            self.picture.setPixmap(QPixmap.fromImage(img))
            time.sleep(0.001)
        cap.release()
        self.action.setText('选择视频')
        self.camera_open = False
        self.signal.emit('视频检测已停止!', 'video')
        self.picture.setPixmap(QPixmap(""))

    def open_image(self):
        imgName, imgType = QFileDialog.getOpenFileName(self, "打开图片", "",
                                                       "图片文件 (*.jpg *.jpeg *.bmp *.png);;All Files(*)")
        if imgName == "":
            return
        self.image_path = imgName
        self.ssl_show.setText("正在检测{}".format(os.path.basename(imgName)))
        threading.Thread(target=self.start_image).start()

    def get_result_str(self, result_list):
        result_dict = {}
        for result in result_list:
            name = result[0]
            if name in result_dict.keys():
                result_dict[name] += 1
            else:
                result_dict[name] = 1
        res = ''
        for k, v in result_dict.items():
            res += k + ":" + str(v) + "\n"
        return res

    def start_image(self):
        frame = cv2.imread(self.image_path)

        result_lists = self.detector.inference_image(frame, False, self.dsb_conf.value(), self.dsb_iou.value())
        frame = self.detector.draw_image(result_lists, frame)
        frame=cv2.resize(frame,(640,480))
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        img = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
        self.picture.setPixmap(QPixmap.fromImage(img))
        res = self.get_result_str(result_lists)
        self.signal.emit(res,'res')
        self.ssl_show.setText("检测已完成!")

    def iou_change(self):
        value = self.hs_iou.value() / 100
        self.dsb_iou.setValue(value)

    def conf_change(self):
        value = self.hs_conf.value() / 100
        self.dsb_conf.setValue(value)

    def dsb_iou_change(self):
        value = int(self.dsb_iou.value() * 100)
        self.hs_iou.setValue(value)

    def dsb_conf_change(self):
        value = int(self.dsb_conf.value() * 100)
        self.hs_conf.setValue(value)

    def load_weights_to_list(self):
        for file in os.listdir(self.weights_dir):
            if file.endswith(".onnx") or file.endswith(".pt"):
                self.cb_weights.addItem(file)

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("MainWindow", "铁塔巡检内部测试系统"))
        self.picture.setText(_translate("MainWindow", "TextLabel"))
        self.label_2.setText(_translate("MainWindow",
                                        "<html><head/><body><p><span style=\" font-size:11pt;\">模型选择</span></p></body></html>"))
        self.label_3.setText(_translate("MainWindow",
                                        "<html><head/><body><p><span style=\" font-size:11pt;\">置信度</span></p></body></html>"))
        self.label_4.setText(_translate("MainWindow",
                                        "<html><head/><body><p><span style=\" font-size:11pt;\">IOU</span></p></body></html>"))
        self.label_5.setText(_translate("MainWindow",
                                        "<html><head/><body><p><span style=\" font-size:11pt;\">结果统计</span></p></body></html>"))
        self.toolBar.setWindowTitle(_translate("MainWindow", "toolBar"))
        self.actionopenpic.setText(_translate("MainWindow", "选择图片"))
        self.action.setText(_translate("MainWindow", "选择视频"))
        self.action_2.setText(_translate("MainWindow", "打开摄像头"))
        self.actionexit.setText(_translate("MainWindow", "退出程序"))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    ui = Ui_MainWindow()
    ui.setupUi()
    ui.show()
    sys.exit(app.exec_())
