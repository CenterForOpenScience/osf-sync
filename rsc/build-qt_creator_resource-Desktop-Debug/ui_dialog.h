/********************************************************************************
** Form generated from reading UI file 'dialog.ui'
**
** Created by: Qt User Interface Compiler version 5.4.1
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_DIALOG_H
#define UI_DIALOG_H

#include <QtCore/QVariant>
#include <QtWidgets/QAction>
#include <QtWidgets/QApplication>
#include <QtWidgets/QButtonGroup>
#include <QtWidgets/QCheckBox>
#include <QtWidgets/QDialog>
#include <QtWidgets/QGroupBox>
#include <QtWidgets/QHeaderView>
#include <QtWidgets/QLabel>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QRadioButton>
#include <QtWidgets/QTabWidget>
#include <QtWidgets/QTextEdit>
#include <QtWidgets/QTreeWidget>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_Preferences
{
public:
    QWidget *verticalLayoutWidget;
    QVBoxLayout *verticalLayout;
    QTabWidget *tabWidget;
    QWidget *tab;
    QGroupBox *groupBox;
    QCheckBox *checkBox;
    QCheckBox *checkBox_2;
    QWidget *tab_2;
    QGroupBox *groupBox_2;
    QGroupBox *groupBox_3;
    QLabel *label;
    QPushButton *pushButton;
    QGroupBox *groupBox_4;
    QGroupBox *groupBox_5;
    QRadioButton *radioButton;
    QRadioButton *radioButton_2;
    QPushButton *pushButton_2;
    QGroupBox *groupBox_6;
    QPushButton *pushButton_3;
    QTextEdit *textEdit;
    QWidget *tab_3;
    QGroupBox *groupBox_7;
    QPushButton *pushButton_4;
    QLineEdit *lineEdit;
    QLineEdit *lineEdit_2;
    QLabel *label_3;
    QLabel *label_5;
    QWidget *tab_4;
    QTreeWidget *treeWidget;
    QLabel *label_2;
    QWidget *tab_5;
    QTextEdit *textEdit_2;

    void setupUi(QDialog *Preferences)
    {
        if (Preferences->objectName().isEmpty())
            Preferences->setObjectName(QStringLiteral("Preferences"));
        Preferences->resize(590, 320);
        verticalLayoutWidget = new QWidget(Preferences);
        verticalLayoutWidget->setObjectName(QStringLiteral("verticalLayoutWidget"));
        verticalLayoutWidget->setGeometry(QRect(0, 0, 591, 321));
        verticalLayout = new QVBoxLayout(verticalLayoutWidget);
        verticalLayout->setObjectName(QStringLiteral("verticalLayout"));
        verticalLayout->setContentsMargins(0, 0, 0, 0);
        tabWidget = new QTabWidget(verticalLayoutWidget);
        tabWidget->setObjectName(QStringLiteral("tabWidget"));
        tab = new QWidget();
        tab->setObjectName(QStringLiteral("tab"));
        groupBox = new QGroupBox(tab);
        groupBox->setObjectName(QStringLiteral("groupBox"));
        groupBox->setGeometry(QRect(10, 20, 551, 80));
        checkBox = new QCheckBox(groupBox);
        checkBox->setObjectName(QStringLiteral("checkBox"));
        checkBox->setGeometry(QRect(10, 20, 541, 22));
        checkBox->setChecked(true);
        checkBox_2 = new QCheckBox(groupBox);
        checkBox_2->setObjectName(QStringLiteral("checkBox_2"));
        checkBox_2->setGeometry(QRect(10, 40, 541, 22));
        checkBox_2->setChecked(true);
        tabWidget->addTab(tab, QString());
        tab_2 = new QWidget();
        tab_2->setObjectName(QStringLiteral("tab_2"));
        groupBox_2 = new QGroupBox(tab_2);
        groupBox_2->setObjectName(QStringLiteral("groupBox_2"));
        groupBox_2->setGeometry(QRect(10, 10, 581, 51));
        groupBox_3 = new QGroupBox(groupBox_2);
        groupBox_3->setObjectName(QStringLiteral("groupBox_3"));
        groupBox_3->setGeometry(QRect(280, 50, 561, 51));
        label = new QLabel(groupBox_2);
        label->setObjectName(QStringLiteral("label"));
        label->setGeometry(QRect(30, 16, 411, 31));
        pushButton = new QPushButton(groupBox_2);
        pushButton->setObjectName(QStringLiteral("pushButton"));
        pushButton->setGeometry(QRect(460, 10, 99, 31));
        groupBox_4 = new QGroupBox(tab_2);
        groupBox_4->setObjectName(QStringLiteral("groupBox_4"));
        groupBox_4->setGeometry(QRect(10, 70, 561, 211));
        groupBox_5 = new QGroupBox(groupBox_4);
        groupBox_5->setObjectName(QStringLiteral("groupBox_5"));
        groupBox_5->setGeometry(QRect(20, 110, 541, 81));
        radioButton = new QRadioButton(groupBox_5);
        radioButton->setObjectName(QStringLiteral("radioButton"));
        radioButton->setGeometry(QRect(30, 20, 117, 22));
        radioButton_2 = new QRadioButton(groupBox_5);
        radioButton_2->setObjectName(QStringLiteral("radioButton_2"));
        radioButton_2->setGeometry(QRect(30, 40, 117, 22));
        pushButton_2 = new QPushButton(groupBox_5);
        pushButton_2->setObjectName(QStringLiteral("pushButton_2"));
        pushButton_2->setGeometry(QRect(440, 20, 99, 31));
        groupBox_6 = new QGroupBox(groupBox_4);
        groupBox_6->setObjectName(QStringLiteral("groupBox_6"));
        groupBox_6->setGeometry(QRect(20, 40, 561, 61));
        pushButton_3 = new QPushButton(groupBox_6);
        pushButton_3->setObjectName(QStringLiteral("pushButton_3"));
        pushButton_3->setGeometry(QRect(440, 20, 99, 31));
        textEdit = new QTextEdit(groupBox_6);
        textEdit->setObjectName(QStringLiteral("textEdit"));
        textEdit->setGeometry(QRect(20, 20, 331, 31));
        tabWidget->addTab(tab_2, QString());
        tab_3 = new QWidget();
        tab_3->setObjectName(QStringLiteral("tab_3"));
        groupBox_7 = new QGroupBox(tab_3);
        groupBox_7->setObjectName(QStringLiteral("groupBox_7"));
        groupBox_7->setGeometry(QRect(50, 40, 441, 181));
        pushButton_4 = new QPushButton(groupBox_7);
        pushButton_4->setObjectName(QStringLiteral("pushButton_4"));
        pushButton_4->setGeometry(QRect(330, 150, 99, 27));
        lineEdit = new QLineEdit(groupBox_7);
        lineEdit->setObjectName(QStringLiteral("lineEdit"));
        lineEdit->setGeometry(QRect(160, 30, 261, 27));
        lineEdit_2 = new QLineEdit(groupBox_7);
        lineEdit_2->setObjectName(QStringLiteral("lineEdit_2"));
        lineEdit_2->setGeometry(QRect(160, 70, 261, 27));
        label_3 = new QLabel(groupBox_7);
        label_3->setObjectName(QStringLiteral("label_3"));
        label_3->setGeometry(QRect(70, 26, 61, 31));
        label_5 = new QLabel(groupBox_7);
        label_5->setObjectName(QStringLiteral("label_5"));
        label_5->setGeometry(QRect(70, 70, 81, 31));
        tabWidget->addTab(tab_3, QString());
        tab_4 = new QWidget();
        tab_4->setObjectName(QStringLiteral("tab_4"));
        treeWidget = new QTreeWidget(tab_4);
        QTreeWidgetItem *__qtreewidgetitem = new QTreeWidgetItem();
        __qtreewidgetitem->setTextAlignment(1, Qt::AlignJustify|Qt::AlignVCenter);
        __qtreewidgetitem->setTextAlignment(0, Qt::AlignJustify|Qt::AlignVCenter);
        treeWidget->setHeaderItem(__qtreewidgetitem);
        QTreeWidgetItem *__qtreewidgetitem1 = new QTreeWidgetItem(treeWidget);
        QTreeWidgetItem *__qtreewidgetitem2 = new QTreeWidgetItem(__qtreewidgetitem1);
        __qtreewidgetitem2->setCheckState(1, Qt::Unchecked);
        QTreeWidgetItem *__qtreewidgetitem3 = new QTreeWidgetItem(__qtreewidgetitem2);
        new QTreeWidgetItem(__qtreewidgetitem3);
        QTreeWidgetItem *__qtreewidgetitem4 = new QTreeWidgetItem(__qtreewidgetitem3);
        new QTreeWidgetItem(__qtreewidgetitem4);
        QTreeWidgetItem *__qtreewidgetitem5 = new QTreeWidgetItem(__qtreewidgetitem1);
        __qtreewidgetitem5->setCheckState(1, Qt::Unchecked);
        QTreeWidgetItem *__qtreewidgetitem6 = new QTreeWidgetItem(__qtreewidgetitem1);
        new QTreeWidgetItem(__qtreewidgetitem6);
        new QTreeWidgetItem(__qtreewidgetitem6);
        new QTreeWidgetItem(__qtreewidgetitem6);
        treeWidget->setObjectName(QStringLiteral("treeWidget"));
        treeWidget->setGeometry(QRect(10, 40, 561, 221));
        treeWidget->setSortingEnabled(false);
        treeWidget->setAnimated(false);
        treeWidget->setWordWrap(false);
        treeWidget->setHeaderHidden(false);
        treeWidget->header()->setVisible(false);
        treeWidget->header()->setCascadingSectionResizes(true);
        treeWidget->header()->setHighlightSections(true);
        label_2 = new QLabel(tab_4);
        label_2->setObjectName(QStringLiteral("label_2"));
        label_2->setGeometry(QRect(10, 10, 561, 17));
        tabWidget->addTab(tab_4, QString());
        tab_5 = new QWidget();
        tab_5->setObjectName(QStringLiteral("tab_5"));
        textEdit_2 = new QTextEdit(tab_5);
        textEdit_2->setObjectName(QStringLiteral("textEdit_2"));
        textEdit_2->setGeometry(QRect(20, 20, 551, 251));
        tabWidget->addTab(tab_5, QString());

        verticalLayout->addWidget(tabWidget);


        retranslateUi(Preferences);

        tabWidget->setCurrentIndex(3);


        QMetaObject::connectSlotsByName(Preferences);
    } // setupUi

    void retranslateUi(QDialog *Preferences)
    {
        Preferences->setWindowTitle(QApplication::translate("Preferences", "Preferences", 0));
        groupBox->setTitle(QApplication::translate("Preferences", "System", 0));
        checkBox->setText(QApplication::translate("Preferences", "Show Desktop Notifications", 0));
        checkBox_2->setText(QApplication::translate("Preferences", "Start OSF Offline on Computer Startup", 0));
        tabWidget->setTabText(tabWidget->indexOf(tab), QApplication::translate("Preferences", "General", 0));
        groupBox_2->setTitle(QApplication::translate("Preferences", "Account", 0));
        groupBox_3->setTitle(QApplication::translate("Preferences", "Account", 0));
        label->setText(QApplication::translate("Preferences", "User name", 0));
        pushButton->setText(QApplication::translate("Preferences", "Log Out", 0));
        groupBox_4->setTitle(QApplication::translate("Preferences", "Project", 0));
        groupBox_5->setTitle(QApplication::translate("Preferences", "Choose Project to Sync With", 0));
        radioButton->setText(QApplication::translate("Preferences", "Project A", 0));
        radioButton_2->setText(QApplication::translate("Preferences", "Project B", 0));
        pushButton_2->setText(QApplication::translate("Preferences", "Change", 0));
        groupBox_6->setTitle(QApplication::translate("Preferences", "Choose Folder to Place Project in ", 0));
        pushButton_3->setText(QApplication::translate("Preferences", "Change", 0));
        textEdit->setHtml(QApplication::translate("Preferences", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:'Ubuntu'; font-size:11pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">/home/himanshu/somefolder/My Project</p></body></html>", 0));
        tabWidget->setTabText(tabWidget->indexOf(tab_2), QApplication::translate("Preferences", "OSF (logged in)", 0));
        groupBox_7->setTitle(QApplication::translate("Preferences", "Log in", 0));
        pushButton_4->setText(QApplication::translate("Preferences", "Log In", 0));
        label_3->setText(QApplication::translate("Preferences", "Email", 0));
        label_5->setText(QApplication::translate("Preferences", "Password", 0));
        tabWidget->setTabText(tabWidget->indexOf(tab_3), QApplication::translate("Preferences", "OSF (logged out)", 0));
        QTreeWidgetItem *___qtreewidgetitem = treeWidget->headerItem();
        ___qtreewidgetitem->setText(1, QApplication::translate("Preferences", "Priority", 0));
        ___qtreewidgetitem->setText(0, QApplication::translate("Preferences", "Component, Folder, or File", 0));

        const bool __sortingEnabled = treeWidget->isSortingEnabled();
        treeWidget->setSortingEnabled(false);
        QTreeWidgetItem *___qtreewidgetitem1 = treeWidget->topLevelItem(0);
        ___qtreewidgetitem1->setText(0, QApplication::translate("Preferences", "My Project", 0));
        QTreeWidgetItem *___qtreewidgetitem2 = ___qtreewidgetitem1->child(0);
        ___qtreewidgetitem2->setText(0, QApplication::translate("Preferences", "My other Component", 0));
        QTreeWidgetItem *___qtreewidgetitem3 = ___qtreewidgetitem2->child(0);
        ___qtreewidgetitem3->setText(0, QApplication::translate("Preferences", "folder a", 0));
        QTreeWidgetItem *___qtreewidgetitem4 = ___qtreewidgetitem3->child(0);
        ___qtreewidgetitem4->setText(0, QApplication::translate("Preferences", "New Item", 0));
        QTreeWidgetItem *___qtreewidgetitem5 = ___qtreewidgetitem3->child(1);
        ___qtreewidgetitem5->setText(0, QApplication::translate("Preferences", "folder b", 0));
        QTreeWidgetItem *___qtreewidgetitem6 = ___qtreewidgetitem5->child(0);
        ___qtreewidgetitem6->setText(0, QApplication::translate("Preferences", "some file", 0));
        QTreeWidgetItem *___qtreewidgetitem7 = ___qtreewidgetitem1->child(1);
        ___qtreewidgetitem7->setText(0, QApplication::translate("Preferences", "My Component", 0));
        QTreeWidgetItem *___qtreewidgetitem8 = ___qtreewidgetitem1->child(2);
        ___qtreewidgetitem8->setText(0, QApplication::translate("Preferences", "C component", 0));
        QTreeWidgetItem *___qtreewidgetitem9 = ___qtreewidgetitem8->child(0);
        ___qtreewidgetitem9->setText(0, QApplication::translate("Preferences", "wiki", 0));
        QTreeWidgetItem *___qtreewidgetitem10 = ___qtreewidgetitem8->child(1);
        ___qtreewidgetitem10->setText(0, QApplication::translate("Preferences", "folder", 0));
        QTreeWidgetItem *___qtreewidgetitem11 = ___qtreewidgetitem8->child(2);
        ___qtreewidgetitem11->setText(0, QApplication::translate("Preferences", "folder", 0));
        treeWidget->setSortingEnabled(__sortingEnabled);

        label_2->setText(QApplication::translate("Preferences", "Priority Items will be given priority when syncing", 0));
        tabWidget->setTabText(tabWidget->indexOf(tab_4), QApplication::translate("Preferences", "Priority Syncing", 0));
        textEdit_2->setHtml(QApplication::translate("Preferences", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:'Ubuntu'; font-size:11pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright "
                        "info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. This is copyright info. </p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p align=\"center\" style=\" margin-top:0px; margin-botto"
                        "m:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">\302\251 Center for Open Science</p></body></html>", 0));
        tabWidget->setTabText(tabWidget->indexOf(tab_5), QApplication::translate("Preferences", "About", 0));
    } // retranslateUi

};

namespace Ui {
    class Preferences: public Ui_Preferences {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_DIALOG_H
