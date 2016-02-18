# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './osfoffline/gui/qt/static/login.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_login(object):
    def setupUi(self, login):
        login.setObjectName("login")
        login.resize(280, 177)
        self.gridLayout = QtWidgets.QGridLayout(login)
        self.gridLayout.setContentsMargins(11, 11, 11, 11)
        self.gridLayout.setSpacing(6)
        self.gridLayout.setObjectName("gridLayout")
        self.groupBox_7 = QtWidgets.QGroupBox(login)
        self.groupBox_7.setObjectName("groupBox_7")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox_7)
        self.gridLayout_2.setContentsMargins(11, 11, 11, 11)
        self.gridLayout_2.setSpacing(6)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.passwordEdit = QtWidgets.QLineEdit(self.groupBox_7)
        self.passwordEdit.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.passwordEdit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.passwordEdit.setObjectName("passwordEdit")
        self.gridLayout_2.addWidget(self.passwordEdit, 1, 1, 1, 1)
        self.label_7 = QtWidgets.QLabel(self.groupBox_7)
        self.label_7.setObjectName("label_7")
        self.gridLayout_2.addWidget(self.label_7, 1, 0, 1, 1)
        self.usernameEdit = QtWidgets.QLineEdit(self.groupBox_7)
        self.usernameEdit.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.usernameEdit.setObjectName("usernameEdit")
        self.gridLayout_2.addWidget(self.usernameEdit, 0, 1, 1, 1)
        self.logInButton = QtWidgets.QPushButton(self.groupBox_7)
        self.logInButton.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.logInButton.setObjectName("logInButton")
        self.gridLayout_2.addWidget(self.logInButton, 2, 1, 1, 1)
        self.label_6 = QtWidgets.QLabel(self.groupBox_7)
        self.label_6.setObjectName("label_6")
        self.gridLayout_2.addWidget(self.label_6, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.groupBox_7, 1, 0, 1, 1)
        self.label = QtWidgets.QLabel(login)
        font = QtGui.QFont()
        font.setPointSize(20)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.retranslateUi(login)
        QtCore.QMetaObject.connectSlotsByName(login)
        login.setTabOrder(self.usernameEdit, self.passwordEdit)
        login.setTabOrder(self.passwordEdit, self.logInButton)

    def retranslateUi(self, login):
        _translate = QtCore.QCoreApplication.translate
        login.setWindowTitle(_translate("login", "OSF Sync | Log in"))
        self.groupBox_7.setTitle(_translate("login", "Log in"))
        self.label_7.setText(_translate("login", "Password:"))
        self.logInButton.setText(_translate("login", "Log In"))
        self.label_6.setText(_translate("login", " Email:"))
        self.label.setText(_translate("login", "Welcome to OSF Sync"))

