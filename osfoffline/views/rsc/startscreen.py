# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'osfoffline/views/rsc/gui/startscreen_gui/startscreen.ui'
#
# Created by: PyQt5 UI code generator 5.5
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_startscreen(object):
    def setupUi(self, startscreen):
        startscreen.setObjectName("startscreen")
        startscreen.resize(642, 374)
        self.groupBox_7 = QtWidgets.QGroupBox(startscreen)
        self.groupBox_7.setGeometry(QtCore.QRect(100, 110, 441, 221))
        self.groupBox_7.setObjectName("groupBox_7")
        self.logInButton = QtWidgets.QPushButton(self.groupBox_7)
        self.logInButton.setGeometry(QtCore.QRect(170, 150, 99, 27))
        self.logInButton.setObjectName("logInButton")
        self.label_6 = QtWidgets.QLabel(self.groupBox_7)
        self.label_6.setGeometry(QtCore.QRect(103, 50, 51, 21))
        self.label_6.setObjectName("label_6")
        self.usernameEdit = QtWidgets.QLineEdit(self.groupBox_7)
        self.usernameEdit.setGeometry(QtCore.QRect(160, 50, 261, 21))
        self.usernameEdit.setObjectName("usernameEdit")
        self.label_7 = QtWidgets.QLabel(self.groupBox_7)
        self.label_7.setGeometry(QtCore.QRect(80, 90, 70, 21))
        self.label_7.setObjectName("label_7")
        self.passwordEdit = QtWidgets.QLineEdit(self.groupBox_7)
        self.passwordEdit.setGeometry(QtCore.QRect(160, 90, 261, 21))
        self.passwordEdit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.passwordEdit.setObjectName("passwordEdit")
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
        startscreen.setWindowTitle(_translate("startscreen", "OSF-Offline | Log in"))
        self.groupBox_7.setTitle(_translate("startscreen", "Log in"))
        self.logInButton.setText(_translate("startscreen", "Log In"))
        self.label_6.setText(_translate("startscreen", " Email:"))
        self.label_7.setText(_translate("startscreen", "Password:"))
        self.label.setText(_translate("startscreen", "Welcome to OSF Offline"))
