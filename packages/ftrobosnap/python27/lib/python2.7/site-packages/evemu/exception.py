class EvEmuError(Exception):
    pass


class WrapperError(EvEmuError):
    pass


class ExecutionError(EvEmuError):
    pass


class TestError(EvEmuError):
    pass


class NullFileHandleError(EvEmuError):
    pass


class SkipTest(Exception):
    pass
