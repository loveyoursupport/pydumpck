
import os
import shutil
import time
from typing import List

from .. import configuration
from ..py_package import PackageStruct, PackageDescription
from PyInstaller.utils.cliutils.archive_viewer import get_archive, get_data, get_content, get_archive_content


class CommonDump():

    @property
    def file_struct_pyc(self):
        if not self._file_struct_pyc:
            self._file_struct_pyc = PackageStruct()
        return self._file_struct_pyc

    def __init__(self):
        self._file_struct_pyc: PackageStruct = None
        self.action_dispatch = {
            'nofile': self.handle_nofile,
            'arch': self.handle_arch_file,
            'pyc': self.handle_pyc_file
        }
        self.action_map = {
            'exe': 'arch',
            'pe': 'arch',
            'elf': 'arch',
            'pyz': 'arch',
            'pyc': 'pyc',
        }

    def handle_nofile(self, target_file: str):
        print(target_file, "[-] is an invalid file name!")
        return -1

    @staticmethod
    def build_output_dir(clear=True):
        output_dir = configuration.thread_output_directory
        if clear and os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir

    def handle_pyc_file(self, target_file: str):
        output_dir = self.build_output_dir()
        new_file = f'{output_dir}{os.path.sep}{target_file}'
        shutil.copy(target_file, new_file)
        PackageStruct.decompile_pyc(new_file)

    def handle_arch_file(self, target_file: str):
        output_dir = self.build_output_dir()
        arch = get_archive(target_file)
        self.extract_arch(arch, output_dir)
        self.file_struct_pyc.progress_check()

    @staticmethod
    def load_plugins(plugin):
        def filter_plugin(p):
            n = f'plugin_decompiler_enable_{p}'
            if n not in configuration.__dict__:
                print(f'[!] no plugin named {p}')
                time.sleep(5)
                return None
            return [p, n]
        plugin = [filter_plugin(x) for x in plugin]
        plugin_paths = [x[1] for x in plugin if x]
        print('plugins loaded with', [x[0] for x in plugin if x])
        [setattr(configuration, x, True) for x in plugin_paths]

        if configuration.plugin_decompiler_enable_uncompyle6 and configuration.decompile_file == None:
            print('[!] attention! when use uncompyle6 , you should use --decompile_file specified which file to decompile for faster task.')
            time.sleep(10)

    def main(self, target_file: str, output_directory: str, thread: int = 0, timeout: int = 10, target_file_type: str = None, session_timeout: int = 120, plugin: List = [], decompile_file: List = None, **args):
        configuration.thread_count = thread  # thread
        configuration.thread_timeout = timeout
        configuration.thread_output_directory = output_directory
        configuration.progress_session_timeout = session_timeout
        configuration.decompile_file = dict(
            zip(decompile_file, [True for x in decompile_file])) if decompile_file else None

        CommonDump.load_plugins(plugin)

        print(f'[*] input:{target_file},to:{output_directory}')

        if os.path.exists(output_directory):
            print(f'[+] removing output_directory')
            try:
                shutil.rmtree(output_directory)
            except:
                pass
        file_type = target_file_type or self.get_filetype(target_file)
        dispatch_to = self.action_map.get(file_type, None)
        if not dispatch_to in self.action_dispatch:
            result = f'unkonwn file-type:{file_type}->{dispatch_to}'
        else:
            print(f'[*] start dump target file.')
            time.sleep(3)
            result = self.action_dispatch[dispatch_to](target_file)
        print('[+] completed', result)
        return result

    @staticmethod
    def get_filetype(filepath: str):
        if not isinstance(filepath, str) or not os.path.isfile(filepath):
            return 'nofile'
        header_data: bytes = None
        with open(filepath, 'rb') as f:
            header_data = f.read(0x20)
        if header_data[0:3] == b'MZ\x90':
            return 'exe'
        if header_data[0:4] == b'PYZ\x00':
            return 'pyz'
        if header_data[0:4] == b'\x7fELF':
            return 'elf'
        if header_data.find(bytes.fromhex('e3' + '0' * 14)) > -1:
            return 'pyc'
        return 'TYPE_UNKNOWN'

    def extract_arch(self, arch, current_directory: str):
        if not os.path.exists(current_directory):
            os.makedirs(current_directory)
        children_package = arch.toc
        if isinstance(children_package, dict):
            children_package = filter(
                lambda x: not x.startswith('_'), list(children_package))
        else:
            children_package = children_package.data
        for package in children_package:
            p = PackageDescription(package, arch, current_directory)
            self.file_struct_pyc.add(p)