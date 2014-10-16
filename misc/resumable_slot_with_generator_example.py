#!/usr/bin/env python3

# By Erik Hvatum, 2014.  Copyright waived; the contents of this file represent a trivial example, are public
# domain, and may be used for any purpose and/or relicensed without attribution.


from PyQt5 import Qt

def coroutine(func):
    '''This is meant to act as a decorator.  Its purpose is to call next once for you upon instantiation of
    a generator so that you don't have to.  If you want separate instantiation and execution, for example
    because you wish to make a generator and kick it off later, don't use this.'''
    def start(*args, **kwargs):
        cr = func(*args, **kwargs)
        next(cr)
        return cr
    return start

class Dlg(Qt.QDialog):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.Qt.WA_DeleteOnClose)

        l = Qt.QHBoxLayout()
        self.setLayout(l)

        self.resumable_operation = None
        self.resumable_operation_step_count = 5
        self.resumable_operation_step_time = 2

        self.do_timer = Qt.QTimer(self)
        self.do_timer.setSingleShot(True)
        self.do_timer.timeout.connect(self.do_timer_fired_slot)

        self.do_button = Qt.QPushButton('start')
        self.do_button.clicked.connect(self.do_button_clicked_slot)
        l.addWidget(self.do_button)

        self.abort_button = Qt.QPushButton('abort')
        self.abort_button.clicked.connect(self.abort_button_clicked_slot)
        self.abort_button.setEnabled(False)
        l.addWidget(self.abort_button)

        self.status_label = Qt.QLabel('ready to start')
        l.addWidget(self.status_label)

        self.show()

    def do_button_clicked_slot(self):
        if self.resumable_operation is None:
            self.resumable_operation = self.resumable_operation_proc()
            # Because resumable_operation_proc has the @coroutine decorator, self.resumable_operation.next() has
            # been called and resumable_operation_proc is now executing
        else:
            self.resumable_operation.send(True)

    def abort_button_clicked_slot(self):
        try:
            if self.resumable_operation is not None:
                self.resumable_operation.send(False)
        except StopIteration:
            pass

    def do_timer_fired_slot(self):
        try:
            if self.resumable_operation is not None:
                self.resumable_operation.send(True)
        except StopIteration:
            pass

    @coroutine
    def resumable_operation_proc(self):
        self.do_button.setText('next step')
        self.abort_button.setEnabled(True)

        step = 1
        while True:
            self.do_button.setEnabled(False)
            self.status_label.setText('doing step {}'.format(step))
            self.do_timer.start(self.resumable_operation_step_time * 1000)

            keep_going = yield
            if not keep_going or step == self.resumable_operation_step_count:
                break
            step += 1
            self.do_button.setEnabled(True)
            self.status_label.setText('ready for step {}'.format(step))
            keep_going = yield
            if not keep_going:
                break

        self.do_timer.stop()
        self.do_button.setText('start')
        self.do_button.setEnabled(True)
        self.abort_button.setEnabled(False)
        self.status_label.setText('ready to start')
        self.resumable_operation = None

if __name__ == '__main__':
    import sys
    app = Qt.QApplication(sys.argv)
    dlg = Dlg()
    app.exec_()
