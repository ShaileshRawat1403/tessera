"""Sample module that uses inconsistent terminology on purpose."""


def load_config(cfg_path):
    config = _read(cfg_path)
    return config


def send_message(msg):
    message_queue.append(msg)


class RepositoryClient:
    def repo_url(self):
        return self.repository_url


def _read(path):
    return path
