from marshmallow import Schema, fields, validate

class SettingsSchema(Schema):
    recordLength = fields.Integer(required=True, validate=validate.Range(min=1, max=60))
    fileSize = fields.Integer(required=True, validate=validate.Range(min=10, max=1000))
    autoRecord = fields.Boolean(required=True)
    quality = fields.String(required=True, validate=validate.OneOf(['low', 'medium', 'high']))
    fps = fields.Integer(required=True, validate=validate.OneOf([15, 24, 30]))

def validate_settings(data):
    schema = SettingsSchema()
    return schema.load(data) 