import re
import subprocess


ANSI_ESCAPE = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
COUNT = re.compile(r'(?<!\d)(\d+)\s*/\s*(\d+)(?!\d)')


class UpdateProgress:
    def __init__(self, label, report):
        self.label = label
        self.report = report
        self.phase = 'Preparing'
        self.last = None

    def feed(self, output):
        line = ANSI_ESCAPE.sub('', output).strip()
        if not line:
            return
        lower = line.lower()
        if lower.startswith('infinity os root snapshot #') and lower.endswith(' created.'):
            self.phase = line[len('Infinity OS '):-1].capitalize()
        elif 'updating and loading repositories' in lower:
            self.phase = 'Checking repositories'
        elif 'download' in lower or 'fetching' in lower:
            self.phase = 'Downloading'
        elif any(word in lower for word in ('installing', 'upgrading', 'updating',
                                             'running transaction', 'applying')):
            self.phase = 'Installing'
        elif 'verifying' in lower or 'cleanup' in lower:
            self.phase = 'Finishing'

        match = COUNT.search(line)
        current, total = (int(value) for value in match.groups()) if match else (None, None)
        if total is not None and (total == 0 or current > total):
            current = total = None
        state = (self.phase, current, total)
        if state != self.last:
            self.last = state
            self.report(self.label, *state)


def run_update_command(label, args, report):
    progress = UpdateProgress(label, report)
    progress.report(label, progress.phase, None, None)
    output = []
    try:
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding='utf-8', errors='replace', bufsize=1) as process:
            line = ''
            while char := process.stdout.read(1):
                if char in '\r\n':
                    if line:
                        progress.feed(line)
                        output.append(line)
                        output = output[-30:]
                        line = ''
                elif len(line) < 4096:
                    line += char
            if line:
                progress.feed(line)
                output.append(line)
            return subprocess.CompletedProcess(args, process.wait(), '\n'.join(output), '')
    except OSError as error:
        return subprocess.CompletedProcess(args, 1, '', str(error))
