import logging
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied as DRFPermissionDenied
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def api_response(message='', data=None, status_code=status.HTTP_200_OK):
    return Response(
        {
            'status': status_code,
            'message': message,
            'data': data if data is not None else {},
        },
        status=status_code,
    )


class ExceptionMixin:
    def handle_exception(self, exc):
        from django.http import Http404
        from django.core.exceptions import PermissionDenied as DjPermissionDenied

        if isinstance(exc, Http404):
            exc = NotFound()
        elif isinstance(exc, DjPermissionDenied):
            exc = DRFPermissionDenied()

        if isinstance(exc, APIException):
            detail = exc.detail
            if isinstance(detail, dict):
                first_val = next(iter(detail.values()))
                message = str(first_val[0]) if isinstance(first_val, list) else str(first_val)
            elif isinstance(detail, list):
                message = str(detail[0]) if detail else 'Error.'
            else:
                message = str(detail)
            return api_response(message, status_code=exc.status_code)

        logger.exception('Unhandled exception in %s', self.__class__.__name__)
        return api_response(
            'Something went wrong. Please try again later.',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
