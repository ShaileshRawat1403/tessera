"""Sample module that uses inconsistent terminology on purpose."""


def load_config(cfg_path, cfg_dir):
    config = _read(cfg_path)
    config.update(_read(cfg_dir))
    return config


def send_message(msg):
    message_queue.append(msg)
    return message_queue


class RepositoryClient:
    def repo_url(self):
        return self.repository_url

    def repo_name(self):
        return self.repository_name


def _read(path):
    return {"path": path}
