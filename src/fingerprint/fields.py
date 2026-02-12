from django.db import models


class TruncatedCharField(models.CharField):
    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname)
        if value and len(value) > self.max_length:
            # Silently truncate to fit the DB constraint
            value = value[: self.max_length]
            setattr(model_instance, self.attname, value)
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        if value and len(value) > self.max_length:
            # Silently truncate to fit the DB constraint
            value = value[: self.max_length]
        return super().get_db_prep_value(value, connection, prepared)
