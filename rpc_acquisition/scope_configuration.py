# to change configuration values from these defaults, simply import this
# file and modify the relevant attributes before importing other scope
# modules.

def _make_tcp_host(host, port):
    return 'tcp://{}:{}'.format(host, port)

class Server:
    LOCALHOST = '127.0.0.1'
    PUBLICHOST = '*'
    HOST = LOCALHOST

    RPC_PORT = '6000'
    RPC_INTERRUPT_PORT = '6001'
    PROPERTY_PORT = '6002'

    @classmethod
    def rpc_addr(cls, host=None):
        if host is None:
            host = cls.HOST
        return _make_tcp_host(host, cls.RPC_PORT)

    @classmethod
    def interrupt_addr(cls, host=None):
        if host is None:
            host = cls.HOST
        return _make_tcp_host(host, cls.RPC_INTERRUPT_PORT)

    @classmethod
    def property_addr(cls, host=None):
        if host is None:
            host = cls.HOST
        return _make_tcp_host(host, cls.PROPERTY_PORT)

class Stand:
    SERIAL_PORT = '/dev/ttyScope'
    SERIAL_BAUD = 115200

class Camera:
    MODEL = 'ZYLA-5.5-CL3'
    ACCUMULATE_COUNT_RANGE_EXTREMA = (1, 2147483647)
    AOI_LEFT_RANGE_EXTREMA = (1, 2549)
    AOI_TOP_RANGE_EXTREMA = (1, 2149)
    AOI_WIDTH_RANGE_EXTREMA = (12, 2560)
    AOI_HEIGHT_RANGE_EXTREMA = (12, 2160)
    EXPOSURE_TIME_RANGE_EXTREMA = (0.025409121719763728, 30000.0)
    FRAME_COUNT_RANGE_EXTREMA = (1, 2147483646)
    FRAME_RATE_RANGE_EXTREMA = (1.832619532376591e-05, 39355.94512195122)

class IOTool:
    SERIAL_PORT = '/dev/ttyIOTool'
    LUMENCOR_PINS = {
        'UV': 'D6',
        'Blue': 'D5',
        'Cyan': 'D3',
        'Teal': 'D4',
        'GreenYellow': 'D2',
        'Red': 'D1'
    }

    CAMERA_PINS = {
        'Trigger': 'B0',
        'Arm': 'B1',
        'Fire': 'B2',
        'AuxOut1': 'B3'
    }

    TL_ENABLE_PIN = 'E6'
    TL_PWM_PIN = 'D7'
    TL_PWM_MAX = 255

    FOOTPEDAL_PIN = 'B4'
    FOOTPEDAL_CLOSED_TTL_STATE = False
    FOOTPEDAL_BOUNCE_DELAY_MS = 100

class SpectraX:
    SERIAL_PORT = '/dev/ttySpectraX'
    SERIAL_BAUD = 9600

class Peltier:
    SERIAL_PORT = '/dev/ttyPeltier'
    SERIAL_BAUD = 2400