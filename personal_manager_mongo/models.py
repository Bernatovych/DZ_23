import mongoengine
from mongoengine import EmbeddedDocument, Document, ReferenceField
from mongoengine.fields import EmbeddedDocumentField, ListField, StringField


class Records(Document):
    name = StringField()
    birthday = StringField()


class Phones(Document):
    number = StringField()
    records = ReferenceField(Records, reverse_delete_rule=mongoengine.CASCADE)


class Tags(EmbeddedDocument):
    title = StringField()


class Notes(Document):
    title = StringField()
    records = ReferenceField(Records, reverse_delete_rule=mongoengine.CASCADE)
    tags = ListField(EmbeddedDocumentField(Tags), reverse_delete_rule=mongoengine.CASCADE)


class Addresses(Document):
    title = StringField()
    records = ReferenceField(Records, reverse_delete_rule=mongoengine.CASCADE)


class Emails(Document):
    title = StringField()
    records = ReferenceField(Records, reverse_delete_rule=mongoengine.CASCADE)


