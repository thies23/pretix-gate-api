import secrets

from django.conf import settings
from django.http import JsonResponse
from django.views import View

from pretix.base.models import Device, Gate


class APIError(Exception):
    def __init__(self, message, status=400):
        self.message = message
        self.status = status


class BaseAPIView(View):

    def json_response(self, data, status=200):
        response = JsonResponse(data, status=status)
        response["Cache-Control"] = "no-store"
        return response

    def get_request_body(self, request):
        import json

        try:
            body = json.loads(request.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise APIError("Invalid JSON body.", 400)

        if not isinstance(body, dict):
            raise APIError("JSON body must be an object.", 400)

        return body

    def get_auth_header(self, request):
        header = request.headers.get("Authorization", "")

        if not header:
            raise APIError("Authorization header required.", 401)

        parts = header.split(" ", 1)

        if len(parts) != 2:
            raise APIError("Invalid Authorization header.", 401)

        return parts[0], parts[1]

    def authenticate(self, request):
        scheme, token = self.get_auth_header(request)

        if scheme.lower() == "bearer":
            configured_token = getattr(
                settings,
                "PRETIX_GATE_API_TOKEN",
                None,
            )

            if not configured_token:
                raise APIError(
                    "Plugin API token is not configured.",
                    500,
                )

            if not secrets.compare_digest(
                token,
                str(configured_token),
            ):
                raise APIError(
                    "Invalid API token.",
                    401,
                )

            return {
                "type": "api",
                "device": None,
                "organizer": None,
            }

        if scheme.lower() == "device":
            try:
                device = (
                    Device.objects
                    .select_related("organizer", "gate")
                    .get(
                        api_token=token,
                        revoked=False,
                    )
                )
            except Device.DoesNotExist:
                raise APIError(
                    "Invalid device token.",
                    401,
                )

            return {
                "type": "device",
                "device": device,
                "organizer": device.organizer,
            }

        raise APIError(
            "Unsupported authorization scheme.",
            401,
        )

    def handle_exception(self, exc):
        if isinstance(exc, APIError):
            return self.json_response(
                {
                    "error": exc.message,
                },
                status=exc.status,
            )

        raise exc

    def dispatch(self, request, *args, **kwargs):
        try:
            request.auth_context = self.authenticate(request)

            return super().dispatch(
                request,
                *args,
                **kwargs,
            )

        except APIError as exc:
            return self.handle_exception(exc)


class GateListView(BaseAPIView):

    def get(self, request):
        auth = request.auth_context

        if auth["type"] == "device":
            organizer = auth["organizer"]

        else:
            organizer_slug = request.GET.get("organizer")

            if not organizer_slug:
                return self.json_response(
                    {
                        "error": "organizer parameter is required.",
                    },
                    status=400,
                )

            try:
                from pretix.base.models import Organizer

                organizer = Organizer.objects.get(
                    slug=organizer_slug,
                )
            except Organizer.DoesNotExist:
                return self.json_response(
                    {
                        "error": "Organizer not found.",
                    },
                    status=404,
                )

        gates = Gate.objects.filter(
            organizer=organizer,
        ).order_by("name")

        return self.json_response(
            {
                "gates": [
                    {
                        "id": gate.id,
                        "name": gate.name,
                        "identifier": gate.identifier,
                    }
                    for gate in gates
                ]
            }
        )


class DeviceListView(BaseAPIView):

    def get(self, request):
        auth = request.auth_context

        if auth["type"] == "device":
            organizer = auth["organizer"]
        else:
            organizer_slug = request.GET.get("organizer")

            if not organizer_slug:
                return self.json_response(
                    {
                        "error": "organizer parameter is required.",
                    },
                    status=400,
                )

            try:
                from pretix.base.models import Organizer

                organizer = Organizer.objects.get(
                    slug=organizer_slug,
                )
            except Organizer.DoesNotExist:
                return self.json_response(
                    {
                        "error": "Organizer not found.",
                    },
                    status=404,
                )

        devices = (
            Device.objects
            .filter(organizer=organizer)
            .select_related("gate")
            .order_by("device_id")
        )

        return self.json_response(
            {
                "devices": [
                    {
                        "id": device.id,
                        "device_id": device.device_id,
                        "name": device.name,
                        "unique_serial": device.unique_serial,
                        "revoked": device.revoked,
                        "gate": (
                            {
                                "id": device.gate.id,
                                "name": device.gate.name,
                                "identifier": device.gate.identifier,
                            }
                            if device.gate
                            else None
                        ),
                    }
                    for device in devices
                ]
            }
        )


class DeviceGateView(BaseAPIView):

    def get_device(self, request, device_id):
        auth = request.auth_context

        try:
            device_id = int(device_id)
        except (TypeError, ValueError):
            raise APIError(
                "Invalid device ID.",
                400,
            )

        if auth["type"] == "device":
            authenticated_device = auth["device"]

            if authenticated_device.device_id != device_id:
                raise APIError(
                    "Device token can only access its own device.",
                    403,
                )

            return authenticated_device

        organizer_slug = request.GET.get("organizer")

        if not organizer_slug:
            raise APIError(
                "organizer parameter is required.",
                400,
            )

        try:
            from pretix.base.models import Organizer

            organizer = Organizer.objects.get(
                slug=organizer_slug,
            )
        except Organizer.DoesNotExist:
            raise APIError(
                "Organizer not found.",
                404,
            )

        try:
            return (
                Device.objects
                .select_related("organizer", "gate")
                .get(
                    organizer=organizer,
                    device_id=device_id,
                )
            )
        except Device.DoesNotExist:
            raise APIError(
                "Device not found.",
                404,
            )

    def get(self, request, device_id):
        try:
            device = self.get_device(
                request,
                device_id,
            )

            return self.json_response(
                {
                    "device": {
                        "id": device.id,
                        "device_id": device.device_id,
                        "name": device.name,
                    },
                    "gate": (
                        {
                            "id": device.gate.id,
                            "name": device.gate.name,
                            "identifier": device.gate.identifier,
                        }
                        if device.gate
                        else None
                    ),
                }
            )

        except APIError as exc:
            return self.handle_exception(exc)

    def put(self, request, device_id):
        try:
            device = self.get_device(
                request,
                device_id,
            )

            body = self.get_request_body(request)

            if "gate" not in body:
                raise APIError(
                    'Field "gate" is required.',
                    400,
                )

            gate_value = body["gate"]

            if gate_value is None:
                device.gate = None
                device.save(update_fields=["gate"])

                return self.json_response(
                    {
                        "success": True,
                        "device_id": device.device_id,
                        "gate": None,
                    }
                )

            try:
                gate_id = int(gate_value)
            except (TypeError, ValueError):
                raise APIError(
                    '"gate" must be an integer or null.',
                    400,
                )

            try:
                gate = Gate.objects.get(
                    organizer=device.organizer,
                    id=gate_id,
                )
            except Gate.DoesNotExist:
                raise APIError(
                    "Gate not found.",
                    404,
                )

            device.gate = gate
            device.save(update_fields=["gate"])

            return self.json_response(
                {
                    "success": True,
                    "device_id": device.device_id,
                    "gate": {
                        "id": gate.id,
                        "name": gate.name,
                        "identifier": gate.identifier,
                    },
                }
            )

        except APIError as exc:
            return self.handle_exception(exc)