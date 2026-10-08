"""只持久化复位序号；课堂步骤与执行报告仅存在浏览器内存。"""
import json
from pathlib import Path


DEFAULT_DIRECTORY = Path(__file__).resolve().parents[1] / '.demo-state'


class ResetState:
    def __init__(self, directory=None):
        self.path = Path(directory or DEFAULT_DIRECTORY) / 'reset.json'

    def read(self):
        if not self.path.exists():
            return {'epoch': 0}
        state = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(state.get('epoch'), int) or state['epoch'] < 0:
            raise ValueError('复位状态损坏，请执行 reset_demo')
        return state

    def reset(self):
        try:
            epoch = self.read()['epoch'] + 1
        except (ValueError, OSError):
            epoch = 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'epoch': epoch}) + '\n', encoding='utf-8')
        temporary.replace(self.path)
        return {'epoch': epoch}
