import fire


class Commands:
    def info(self):
        raise NotImplementedError()

    def sources(self):
        raise NotImplementedError()

    def status(self):
        raise NotImplementedError()

    def configure(self):
        raise NotImplementedError()

    def build(self):
        raise NotImplementedError()

    def doc(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError()

    def version_plan(self):
        raise NotImplementedError()

    def packaging_plan(self):
        raise NotImplementedError()

    def apply_plan(self):
        raise NotImplementedError()

    def graphviz(self):
        raise NotImplementedError()


def main():
    fire.Fire(Commands)
