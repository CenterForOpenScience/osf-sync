#include "startup.h"
#include "ui_startup.h"

StartUp::StartUp(QWidget *parent) :
    QDialog(parent),
    ui(new Ui::StartUp)
{
    ui->setupUi(this);
}

StartUp::~StartUp()
{
    delete ui;
}
