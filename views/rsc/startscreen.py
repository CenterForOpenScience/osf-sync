# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'startscreen.ui'
#
# Created by: PyQt5 UI code generator 5.4.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_startscreen(object):
    def setupUi(self, startscreen):
        startscreen.setObjectName("startscreen")
        startscreen.resize(642, 330)
        self.groupBox_7 = QtWidgets.QGroupBox(startscreen)
        self.groupBox_7.setGeometry(QtCore.QRect(100, 110, 441, 181))
        self.groupBox_7.setObjectName("groupBox_7")
        self.logInButton = QtWidgets.QPushButton(self.groupBox_7)
        self.logInButton.setGeometry(QtCore.QRect(330, 150, 99, 27))
        self.logInButton.setObjectName("logInButton")
        self.emailEdit = QtWidgets.QLineEdit(self.groupBox_7)
        self.emailEdit.setGeometry(QtCore.QRect(160, 30, 261, 27))
        self.emailEdit.setObjectName("emailEdit")
        self.passwordEdit = QtWidgets.QLineEdit(self.groupBox_7)
        self.passwordEdit.setGeometry(QtCore.QRect(160, 70, 261, 27))
        self.passwordEdit.setObjectName("passwordEdit")
        self.label_3 = QtWidgets.QLabel(self.groupBox_7)
        self.label_3.setGeometry(QtCore.QRect(70, 26, 61, 31))
        self.label_3.setObjectName("label_3")
        self.label_5 = QtWidgets.QLabel(self.groupBox_7)
        self.label_5.setGeometry(QtCore.QRect(70, 70, 81, 31))
        self.label_5.setObjectName("label_5")
        self.label = QtWidgets.QLabel(startscreen)
        self.label.setGeometry(QtCore.QRect(60, 30, 521, 60))
        font = QtGui.QFont()
        font.setPointSize(20)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")

        self.retranslateUi(startscreen)
        QtCore.QMetaObject.connectSlotsByName(startscreen)

    def retranslateUi(self, startscreen):
        _translate = QtCore.QCoreApplication.translate
        startscreen.setWindowTitle(_translate("startscreen", "startscreen"))
        self.groupBox_7.setTitle(_translate("startscreen", "Log in"))
        self.logInButton.setText(_translate("startscreen", "Log In"))
        self.label_3.setText(_translate("startscreen", "Email"))
        self.label_5.setText(_translate("startscreen", "Password"))
        self.label.setText(_translate("startscreen", "Welcome to OSF Offline"))

