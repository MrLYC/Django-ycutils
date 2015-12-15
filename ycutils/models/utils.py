#!/usr/bin/env python
# encoding: utf-8

from datetime import timedelta

from django.db import models
from django.utils import timezone


class CURDManager(models.Manager):
    def first(self, *args, **kwargs):
        return self.filter(*args, **kwargs).first()

    def last(self, *args, **kwargs):
        return self.filter(*args, **kwargs).last()

    def exists(self, *args, **kwargs):
        return self.filter(*args, **kwargs).exists()

    def count(self, *args, **kwargs):
        return self.filter(*args, **kwargs).count()

    def remove_where(self, *args, **kwargs):
        self.filter(*args, **kwargs).delete()


class BaseModel(models.Model):
    create_at = models.DateTimeField(auto_now_add=True)
    modify_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    unique_fields = {"id"}
    objects = CURDManager()

    def remove(self):
        self.delete()

    def __str__(self):
        return ", ".join(
            "%s=%r" % (f, getattr(self, f))
            for f in self.unique_fields
        )


def _deleted_option_wrapper(method_name):
    def wrapper(self, *args, **kwargs):
        kwargs.setdefault("deleted", False)
        base = super(SoftDelManager, self)
        method = getattr(base, method_name)
        return method(*args, **kwargs)
    return wrapper


class SoftDelManager(CURDManager):
    all = filter = _deleted_option_wrapper("filter")
    get = _deleted_option_wrapper("get")
    get_or_create = _deleted_option_wrapper("get_or_create")
    update_or_create = _deleted_option_wrapper("update_or_create")

    def exclude(self, *args, **kwargs):
        query_option = models.Q(*args, **kwargs)
        if "deleted" not in kwargs:
            query_option = query_option | models.Q(deleted=True)
        return super(SoftDelManager, self).exclude(query_option)

    def delete_expired_objects(self, *args, **kwargs):
        now = timezone.now()
        delta = timedelta(seconds=self.model.safe_retain_time)
        return self.filter(
            deleted=True, modify_time__lt=now - delta,
        ).delete(*args, **kwargs)

    def remove_where(self, *args, **kwargs):
        self.filter(*args, **kwargs).update(deleted=True)


class SoftDelModel(BaseModel):
    deleted = models.BooleanField(
        default=False, null=False, blank=False, db_index=True,
    )

    class Meta:
        abstract = True

    objects = SoftDelManager()
    safe_retain_time = 60 * 60 * 24 * 30  # a month

    def remove(self):
        self.deleted = True
        self.save()
