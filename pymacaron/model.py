from datetime import datetime
from pymacaron.log import pymlogger


log = pymlogger(__name__)


def prune_none(**kwargs):
    """Remove all keys that are set to None and set the pydantic object's
    properties to the remaining ones.

    Usage:
    apipool.myapi.MyModel(**prune_none(**kwargs))

    Pydantic's default __init__(**kwargs)
    sets all properties listed in kwargs, even those that are None. When
    later doing dict(exclude_unset=True), those None properties are kept,
    and we want to avoid that and rely to swagger's x-nullable instead
    """

    for k in list(kwargs.keys()):
        v = kwargs[k]
        if v is None:
            del kwargs[k]
    return kwargs


class PymacaronBaseModel(object):
    """The base class from which all pymacaron model classes inherit. Some of these
    methods are redundant with pydantic, but kept for backward compatibility
    with code using older versions of pymacaron.

    """

    # See https://pydantic-docs.helpmanual.io/usage/exporting_models/ about ujson vs orjson
    class Config:
        # Do type validation each time a property is set
        validate_assignment = True

        # Don't allow extra properties when passing kwargs to __init__()
        extra = 'forbid'

        # # extra json.dumps arguments
        # indent = 4
        # sort_keys = True


    def __str__(self):
        """Return a generic string representation of a pymacaron model instance"""
        return f'{self.get_model_name()}(self.dict())'


    def __set_nullable(self, j, o):
        # Set x-nullable keys to None if they are missing
        for k in o.get_nullable_properties():
            if k not in j:
                j[k] = None
        for k in list(j.keys()):
            v = j[k]
            if type(v) is dict:
                self.__set_nullable(v, getattr(o, k))
            elif type(v) is list:
                for i in range(len(v)):
                    jj = v[i]
                    if type(jj) is dict:
                        self.__set_nullable(jj, getattr(o, k)[i])


    def __serialize_datetime(self, j, f):
        for k, v in j.items():
            if type(v) is datetime:
                j[k] = f(v)
            elif type(v) is dict:
                self.__serialize_datetime(v, f)
            elif type(v) is list:
                for jj in v:
                    if type(jj) is dict:
                        self.__serialize_datetime(jj, f)


    def to_json(self, keep_datetime=False, keep_nullable=False, datetime_encoder=None, exclude_unset=True, exclude_none=False):
        """Return a dictionary representation this PyMacaron object, with datetime
        types serialized to strings.
        """

        # We want a json dict of only the object's properties that have been set.
        # https://stackoverflow.com/questions/66229384/pydantic-detect-if-a-field-value-is-missing-or-given-as-null
        j = self.dict(exclude_unset=exclude_unset, exclude_none=exclude_none)

        # Optionally set nullable fields to None
        if keep_nullable:
            self.__set_nullable(j, self)

        # Optionally serialize datetimes
        if not keep_datetime:
            if not datetime_encoder:
                # The default encoding of datetime is .isoformat()
                self.__serialize_datetime(j, lambda d: d.isoformat())
            else:
                self.__serialize_datetime(j, datetime_encoder)

        return j


    @classmethod
    def from_json(cls, j):
        """Take a json dictionary and return a model instance"""
        return cls.parse_obj(j)


    def clone(self):
        # Deprecated: should use pydantic.copy() instead
        return self.copy(deep=True)


    def get_model_name(self):
        """Return the name of the OpenAPI schema object describing this pymacaron Model instance"""
        return type(self).__name__


    def get_model_api(self):
        """Return the name of the api to which this model belongs"""
        raise Exception("Should be overriden in model declaration")


    def get_property_names(self):
        """Return the names of all of the model's properties"""
        raise Exception("Should be overriden in model declaration")
