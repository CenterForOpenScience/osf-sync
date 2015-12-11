#!/usr/bin/env python
from osfoffline.application.background import BackgroundWorker

background_worker = BackgroundWorker()
# self.background_worker.set_intervention_cb(
background_worker.set_notification_cb(lambda *_, **__: None)
background_worker.run()
