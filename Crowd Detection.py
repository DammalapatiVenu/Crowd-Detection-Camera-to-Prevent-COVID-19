# -*- coding: utf-8 -*-
# Form implementation generated from reading ui file 'Frame.ui'
# Created by: PyQt5 UI code generator 5.15.4
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox
from scipy.spatial import distance as dist
import numpy as np
import imutils,imghdr,cv2,os,time,datetime,smtplib
from email.message import EmailMessage
from PIL import Image as im
import threading

class Detector:
    vs = None
    def detectPeople(self, frame, neural_network, layer_names, personIdx, min_confidence = 0.7, nms_threshold = 0.5):
        (H, W) = frame.shape[:2]
        results = []

        blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (416, 416), swapRB=True, crop=False)
        neural_network.setInput(blob)
        layerOutputs = neural_network.forward(layer_names)

        boxes = []
        centroids = []
        confidences = []

        for output in layerOutputs:
            for detection in output:
                scores = detection[5:]
                classID = np.argmax(scores)
                confidence = scores[classID]

                if classID == personIdx and confidence > min_confidence:
                    box = detection[0:4] * np.array([W, H, W, H])
                    (centerX, centerY, width, height) = box.astype("int")

                    x = int(centerX - (width / 2))
                    y = int(centerY - (height / 2))

                    boxes.append([x, y, int(width), int(height)])
                    centroids.append((centerX, centerY))
                    confidences.append(float(confidence))

        idxs = cv2.dnn.NMSBoxes(boxes, confidences, min_confidence, nms_threshold)

        if len(idxs) > 0:
            for i in idxs.flatten():
                (x, y) = (boxes[i][0], boxes[i][1])
                (w, h) = (boxes[i][2], boxes[i][3])

                r = ((x, y, x + w, y + h), centroids[i])
                results.append(r)

        return results

    #self.stream, self.location, self.dis.text(), self.emailCB.isChecked(), self.email, self.time.text(), self.saveCB.isChecked()
    def socialDistance(self, stream, location, min_distance, email, address, t, save):
        min_distance = int(min_distance)
        min_confidence = 0.7
        nms_threshold = 0.5
        
        t = int(t)*60;
        is_violate = False
        a = time.time()

        try:
            stream = int(stream)
        except:
            pass

        self.vs = cv2.VideoCapture(stream)

        labels = open("coco.names").read().strip().split("\n")
        personIdx = labels.index("person")

        neural_network = cv2.dnn.readNetFromDarknet("yolov3.cfg", "yolov3.weights")
        layer_names = ['yolo_82', 'yolo_94', 'yolo_106']


        (grabbed, frame) = self.vs.read()
        if grabbed:
            img = im.fromarray(frame)
            img.save("Loc.jpg")
            ui.relay.setPixmap(QtGui.QPixmap("Loc.jpg"))
            #ui.relay.adjustSize()
        
        writer = None
        if save:
            x = datetime.datetime.now()
            mark = str(x.strftime("%H"))+'-'+str(x.strftime("%M"))+'-'+str(x.strftime("%S"))
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            writer = cv2.VideoWriter(mark+".avi", fourcc, 25, (frame.shape[1], frame.shape[0]), True)

        while self.vs != None:
            (grabbed, frame) = self.vs.read()
            if not grabbed:
                break

            frame = imutils.resize(frame, width=600)
            results = self.detectPeople(frame, neural_network, layer_names, personIdx, min_confidence, nms_threshold)

            violate = set()

            if len(results) >= 2:
                centroids = np.array([r[1] for r in results])
                D = dist.cdist(centroids, centroids, metric="euclidean")

                for i in range(0, D.shape[0]):
                    for j in range(i + 1, D.shape[1]):
                        if D[i, j] < min_distance:
                            violate.add(i)
                            violate.add(j)


            for (i, (bbox, centroid)) in enumerate(results):
                (startX, startY, endX, endY) = bbox
                (cX, cY) = centroid
                color = (0, 255, 0)

                if i in violate:
                    color = (255, 0, 0)

                cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)
                cv2.circle(frame, (cX, cY), 5, color, 1)
                cv2.line(frame, (10,10), (10+min_distance,10), (255, 0, 0), 2)


            text = "Number of persons detected    : {}".format(len(results))
            #cv2.putText(frame, text, (10, frame.shape[0] - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 255), 3)
            ui.detection.setText(text)
            ui.detection.adjustSize()

            text = "Number of violations detected : {}".format(len(violate))
            #cv2.putText(frame, text, (10, frame.shape[0] - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 255), 3)
            ui.violation.setText(text)
            ui.violation.adjustSize()

            if len(violate)>0 and email:
                data = im.fromarray(frame)
                x = datetime.datetime.now()
                mark = str(x.strftime("%H"))+'-'+str(x.strftime("%M"))+'-'+str(x.strftime("%S"))
                data.save('Violation.jpg')
                is_violate = True
                
                if is_violate and time.time()-a>t:
                    self.send_mail(address, location, mark)
                    is_violate = False
                    a = time.time()

            if writer != None:
                writer.write(frame)

            cv2.imshow("Viswa", frame)
            img = im.fromarray(frame)
            img.save("Loc.jpg")
            ui.relay.setPixmap(QtGui.QPixmap("Loc.jpg"))

            key = cv2.waitKey(1)
            if key == ord("q"):
                break


    def send_mail(self, to, location, mark):
        msg = EmailMessage()
        msg['Subject'] = 'Social distance violation detected at '+location+"."
        msg['From'] = 'Crowd Detector <crowd.detection.idp@gmail.com>'
        msg['To'] = to
        msg.set_content('There is a social distance violation occured at '+location+" during "+mark+".")
        
        with open('Violation.jpg','rb') as f:
            data = f.read()

        msg.add_attachment(data, maintype='image', subtype='jpg', filename=mark)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login('crowd.detection.idp@gmail.com', 'ccmfmxtetioiaixy')
            smtp.send_message(msg)


class Ui_MainWindow(object):
    obj = Detector()
    
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1200, 600)
        
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        
        self.Title = QtWidgets.QLabel(self.centralwidget)
        self.Title.setGeometry(QtCore.QRect(0, 0, 1200, 80))
        font = QtGui.QFont()
        font.setFamily("Gabriola")
        font.setPointSize(36)
        font.setBold(True)
        font.setItalic(True)
        font.setUnderline(False)
        font.setWeight(75)
        self.Title.setFont(font)
        self.Title.setAutoFillBackground(False)
        self.Title.setTextFormat(QtCore.Qt.PlainText)
        self.Title.setAlignment(QtCore.Qt.AlignCenter)
        self.Title.setObjectName("Title")
        
        self.locLabel = QtWidgets.QLabel(self.centralwidget)
        self.locLabel.setGeometry(QtCore.QRect(20, 150, 150, 40))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(18)
        self.locLabel.setFont(font)
        self.locLabel.setObjectName("locLabel")
        
        self.locationIP = QtWidgets.QLineEdit(self.centralwidget)
        self.locationIP.setGeometry(QtCore.QRect(180, 150, 370, 40))
        font = QtGui.QFont()
        font.setFamily("Calibri")
        font.setPointSize(16)
        self.locationIP.setFont(font)
        self.locationIP.setObjectName("locationIP")
        self.locationIP.setText("Location 1")
        
        self.streamLabel = QtWidgets.QLabel(self.centralwidget)
        self.streamLabel.setGeometry(QtCore.QRect(20, 200, 150, 40))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(18)
        self.streamLabel.setFont(font)
        self.streamLabel.setObjectName("streamLabel")
        
        self.streamIP = QtWidgets.QLineEdit(self.centralwidget)
        self.streamIP.setGeometry(QtCore.QRect(180, 200, 370, 40))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(16)
        self.streamIP.setFont(font)
        self.streamIP.setObjectName("StreamIP")
        
        self.disLabel = QtWidgets.QLabel(self.centralwidget)
        self.disLabel.setGeometry(QtCore.QRect(20, 250, 150, 40))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(18)
        self.disLabel.setFont(font)
        self.disLabel.setObjectName("disLabel")
        
        self.dis = QtWidgets.QSpinBox(self.centralwidget)
        self.dis.setGeometry(QtCore.QRect(180, 250, 150, 40))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(16)
        self.dis.setFont(font)
        self.dis.setObjectName("dis")
        self.dis.setMaximum(2000)
        self.dis.setValue(100)

        self.saveCB = QtWidgets.QCheckBox(self.centralwidget)
        self.saveCB.setGeometry(QtCore.QRect(350, 250, 180, 40))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(18)
        self.saveCB.setFont(font)
        self.saveCB.setObjectName("saveCB")
        
        self.emailCB = QtWidgets.QCheckBox(self.centralwidget)
        self.emailCB.setGeometry(QtCore.QRect(20, 300, 180, 40))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(18)
        self.emailCB.setFont(font)
        self.emailCB.setObjectName("emailCB")
        
        self.emailLabel2 = QtWidgets.QLabel(self.centralwidget)
        self.emailLabel2.setGeometry(QtCore.QRect(180, 300, 371, 40))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(18)
        self.emailLabel2.setFont(font)
        self.emailLabel2.setAlignment(QtCore.Qt.AlignCenter)
        self.emailLabel2.setObjectName("emailLabel2")
        
        self.time = QtWidgets.QSpinBox(self.centralwidget)
        self.time.setGeometry(QtCore.QRect(362, 307, 90, 30))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(16)
        self.time.setFont(font)
        self.time.setObjectName("time")
        self.time.setValue(5)

        self.emailLabel = QtWidgets.QLabel(self.centralwidget)
        self.emailLabel.setGeometry(QtCore.QRect(20, 350, 150, 40))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(18)
        self.emailLabel.setFont(font)
        self.emailLabel.setObjectName("emailLabel")
        
        self.emailIP = QtWidgets.QLineEdit(self.centralwidget)
        self.emailIP.setGeometry(QtCore.QRect(180, 350, 370, 40))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(16)
        self.emailIP.setFont(font)
        self.emailIP.setObjectName("emailIP")
        self.emailIP.setText("crowd.detection.idp@gmail.com")
        
        self.startButton = QtWidgets.QPushButton(self.centralwidget)
        self.startButton.setGeometry(QtCore.QRect(100, 410, 191, 41))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(18)
        font.setBold(False)
        font.setWeight(50)
        self.startButton.setFont(font)
        self.startButton.setObjectName("startButton")
        
        self.stopButton = QtWidgets.QPushButton(self.centralwidget)
        self.stopButton.setGeometry(QtCore.QRect(290, 410, 191, 41))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(18)
        font.setBold(False)
        font.setWeight(50)
        self.stopButton.setFont(font)
        self.stopButton.setObjectName("stopButton")

        self.relay = QtWidgets.QLabel(self.centralwidget)
        self.relay.setGeometry(QtCore.QRect(575, 80, 600, 500))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Ignored)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.relay.sizePolicy().hasHeightForWidth())
        self.relay.setSizePolicy(sizePolicy)
        self.relay.setText("")
        self.relay.setPixmap(QtGui.QPixmap("Loc.jpg"))
        self.relay.setScaledContents(False)
        self.relay.setAlignment(QtCore.Qt.AlignCenter)
        self.relay.setObjectName("relay")

        self.detection = QtWidgets.QLabel(self.centralwidget)
        self.detection.setGeometry(QtCore.QRect(20, 470, 150, 40))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(18)
        self.detection.setFont(font)
        self.detection.setObjectName("detection")

        self.violation = QtWidgets.QLabel(self.centralwidget)
        self.violation.setGeometry(QtCore.QRect(20, 510, 150, 40))
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(18)
        self.violation.setFont(font)
        self.violation.setObjectName("violation")

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.startButton.clicked.connect(self.startDetection)
        self.stopButton.clicked.connect(self.stopDetection)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.Title.setText(_translate("MainWindow", "Crowd Detector"))
        self.locLabel.setText(_translate("MainWindow", "Location : "))
        self.streamLabel.setText(_translate("MainWindow", "Stream Input : "))
        self.saveCB.setText(_translate("MainWindow", "Save Output"))
        self.emailCB.setText(_translate("MainWindow", "E-Mail Alerts"))
        self.startButton.setText(_translate("MainWindow", "Start Detection"))
        self.disLabel.setText(_translate("MainWindow", "Min Distance : "))
        self.stopButton.setText(_translate("MainWindow", "Stop Detection"))
        self.emailLabel.setText(_translate("MainWindow", "E-Mail ID : "))
        self.emailLabel2.setText(_translate("MainWindow", "Alert for every                  (mins)"))
        self.detection.setText(_translate("MainWindow", "Number of persons detected    : "))
        self.detection.adjustSize()
        self.violation.setText(_translate("MainWindow", "Number of Violations detected : "))
        self.violation.adjustSize()


    def startDetection(self):
        if self.locationIP.text() == "":
            msg = QMessageBox()
            msg.setWindowTitle("Caution")
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Location field is Empty")
            x = msg.exec_()
            return None
        else:
            self.location = self.locationIP.text()
            #print(self.location)

        if self.streamIP.text() == "":
            msg = QMessageBox()
            msg.setWindowTitle("Caution")
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Stream Input field is Empty")
            x = msg.exec_()
            return None
        else:
            self.stream = self.streamIP.text()
            #print(self.stream)
        
        if self.emailIP.text() == "" and self.emailCB.isChecked():
            msg = QMessageBox()
            msg.setWindowTitle("Caution")
            msg.setIcon(QMessageBox.Warning)
            msg.setText("E-Mail field is Empty")
            x = msg.exec_()
            return None
        else:
            self.email = self.emailIP.text()
            #print(self.email)

        self.locationIP.setEnabled(False)
        self.streamIP.setEnabled(False)
        self.dis.setEnabled(False)
        self.time.setEnabled(False)
        self.emailIP.setEnabled(False)
        self.emailCB.setEnabled(False)
        self.saveCB.setEnabled(False)
        self.startButton.setEnabled(False)
        self.obj.socialDistance(self.stream, self.location, self.dis.text(), self.emailCB.isChecked(), self.email, self.time.text(), self.saveCB.isChecked())


    def stopDetection(self):
        self.obj.vs = None
        self.locationIP.setEnabled(True)
        self.streamIP.setEnabled(True)
        self.dis.setEnabled(True)
        self.time.setEnabled(True)
        self.emailIP.setEnabled(True)
        self.emailCB.setEnabled(True)
        self.saveCB.setEnabled(True)
        self.startButton.setEnabled(True)


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
