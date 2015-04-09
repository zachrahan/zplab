# to execute in IPython:
# from ris_widget.ris_widget import RisWidget
# %run -in benchmark.ipy
#
# to re-run benchmark in the same IPython session thereafter:
# rw.image_data=ims[0]

if __name__ == '__main__':
    from ris_widget.ris_widget import RisWidget
    from PyQt5 import Qt
    from pathlib import Path
    import sys
    app = Qt.QApplication(sys.argv)

rw=RisWidget()
rw.show()

import freeimage
import time
shown_count = 0
last_show_time = 0
ims = [freeimage.read(str(p)) for p in sorted(Path('/mnt/scopearray/Zhang_William/allyl_validation/light_0002').glob('allyl_validation__light_0002_*_bf.png'))[:40]]

def on_image_changed():
    global shown_count
    global last_show_time
    if shown_count > 100:
        shown_count = 0
        return
    t = time.time()
    if shown_count != 0 and shown_count % 10 == 0:
        print(shown_count, 1/(t-last_show_time))
    last_show_time = t
    shown_count += 1
    rw.image_data=ims[shown_count % len(ims)]

rw.image_changed.connect(on_image_changed, Qt.Qt.QueuedConnection)
rw.image_data = ims[0]

if __name__ == '__main__':
    app.exec()
