"""Regroupement des sessions d'une application sur toutes les sorties Windows."""


class ApplicationVolume:
    def __init__(self):
        self.controls = []
        self.outputs = []

    def add(self, control, output):
        self.controls.append(control)
        if output not in self.outputs:
            self.outputs.append(output)

    def _read(self, method):
        values = []
        for control in self.controls:
            try:
                values.append(getattr(control, method)())
            except Exception:
                continue
        if not values:
            raise RuntimeError("Aucune session audio disponible")
        return values

    def _write(self, method, value, context):
        succeeded = False
        for control in self.controls:
            try:
                getattr(control, method)(value, context)
                succeeded = True
            except Exception:
                continue
        if not succeeded:
            raise RuntimeError("Aucune session audio disponible")

    def GetMasterVolume(self):
        # Si les sessions diffèrent, afficher le niveau le plus élevé.
        return max(self._read("GetMasterVolume"))

    def GetMute(self):
        return all(self._read("GetMute"))

    def SetMasterVolume(self, value, context):
        self._write("SetMasterVolume", value, context)

    def SetMute(self, value, context):
        self._write("SetMute", value, context)


def collect_application_volumes(devices, make_session, control_interface, volume_interface):
    apps = {}
    for device in devices:
        try:
            enumerator = device.AudioSessionManager.GetSessionEnumerator()
            count = enumerator.GetCount()
        except Exception:
            continue
        for index in range(count):
            try:
                session = make_session(enumerator.GetSession(index).QueryInterface(control_interface))
                # Les sessions inactives restent pilotables, les sessions expirées non.
                if session.State == 2:
                    continue
                process = session.Process
                if process is None:
                    continue
                name = process.name().lower().removesuffix(".exe")
                if not name:
                    continue
                control = session._ctl.QueryInterface(volume_interface)
                apps.setdefault(name, ApplicationVolume()).add(control, device.FriendlyName)
            except Exception:
                # Un processus terminé ou inaccessible ne masque pas les suivants.
                continue
    return apps
