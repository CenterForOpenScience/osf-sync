#ifndef STARTUP_H
#define STARTUP_H

#include <QDialog>

namespace Ui {
class StartUp;
}

class StartUp : public QDialog
{
    Q_OBJECT
    
public:
    explicit StartUp(QWidget *parent = 0);
    ~StartUp();
    
private:
    Ui::StartUp *ui;
};

#endif // STARTUP_H
