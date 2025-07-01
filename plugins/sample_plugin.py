from plugin_api import PluginBase

class SamplePlugin(PluginBase):
    """Пример плагина, который пишет сообщение при активации."""

    def activate(self):
        self.app.logger.info("SamplePlugin activated")

    def deactivate(self):
        self.app.logger.info("SamplePlugin deactivated")
