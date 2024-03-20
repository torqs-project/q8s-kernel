from time import time
from ipykernel.kernelbase import Kernel
import logging
import subprocess
from .k8s import execute

USE_KUBERNETES = True

class Q8sKernel(Kernel):
    implementation = 'q8s-kernel'
    implementation_version = '0.'
    language = 'no-op'
    language_version = '0.1'
    language_info = {
        'name': 'Any text',
        'mimetype': 'text/plain',
        'file_extension': '.txt',
    }
    banner = "q8s"

    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        
        if USE_KUBERNETES:
            start = time()
            output = execute(code)

            stream_content = {'name': 'stdout', 'text': output + f"\nExecution time: {time() - start:.2f} seconds"}
            self.send_response(self.iopub_socket, 'stream', stream_content)
        else:
            if not silent:
                # Write the code to a new Python file
                with open('temp.py', 'w') as f:
                    f.write(code)

            # Use subprocess to execute the file and capture the output and possible errors
            result = subprocess.run(['python', 'temp.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode('utf-8')
            errors = result.stderr.decode('utf-8')

            stream_content = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)

            if errors:
                error_content = {'name': 'stderr', 'text': errors}
                self.send_response(self.iopub_socket, 'stream', error_content)

            # Log the output and errors to the console and write them to a file
            logging.info(output)
            logging.error(errors)
            with open('output.txt', 'a') as f:
                print(output, file=f)
                if errors:
                    print(errors, file=f)

        return {'status': 'ok',
                # The base class increments the execution count
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
               }