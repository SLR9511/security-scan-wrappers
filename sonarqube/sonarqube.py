import json, ast
import subprocess
import urllib
import shutil 
import os
import random
import string
import base64
import boto3
import time
import codecs
from hashlib import md5
from Crypto.Cipher import AES
from Crypto.Util import Counter
import requests
import re

#root = "./"
root = "/sonarqube-scanner/"
oc_namespace = os.environ.get('OC_NAMESPACE')
sonar_server_service = "sonar-server-service"
mis_sqs_secret = base64.b64decode(os.environ.get('MIS_SQS_SECRET'))
mis_sqs_key = os.environ.get('MIS_SQS_KEY')
sqs_queue_name = os.environ.get('QUEUE_NAME')


def code_scanner(URL, Token, message):
    ps = subprocess.Popen("ps -a | grep sonar-scanner", shell = True, stdout = subprocess.PIPE)
    output = ps.stdout.read().split('\n')[:-1]
    ps.stdout.close()
    num = len(output) - 2
    if num <= 50:
        if "github" in URL:
            link = URL
        else:
            link = URL.split("@")[0] + ":" + urllib.quote_plus(Token) + "@" + URL.split("@")[1]
            
        # get project code
        try:
            git = subprocess.Popen("git clone " + link, shell = True, stdout = subprocess.PIPE)
            git.wait()
            git.stdout.close()
        except Exception as e:
            print e
            os.system('rm -rf ' + URL.split("/")[-1].split('.')[0])
            message.delete()
            return False, str(e)

        # get sonar-server service ip
        try:
            service_ip = subprocess.Popen("dig " + sonar_server_service + "." + oc_namespace + ".svc.cluster.local | grep IN", shell = True, stdout = subprocess.PIPE)
            service_ip.wait()
            ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}',service_ip.stdout.read().split('\n')[-2])[0]
        except Exception as e:
            print e
            os.system('rm -rf ' + URL.split("/")[-1].split('.')[0])
            message.delete()
            return False, str(e)

        # write scanner property file, two files should be updated.
        project = URL.split("/")[-1].split('.')[0]
        src = root + 'sonar-project.properties'
        dst = root + project
        try:
            cp = subprocess.Popen("cp " + src + " " + dst, shell = True, stdout = subprocess.PIPE)
            cp.wait()
            cp.stdout.close()
        except Exception as e:
            print e
            os.system('rm -rf ' + URL.split("/")[-1].split('.')[0])
            message.delete()
            return False, str(e)
        try:
            f = open(root + project + '/sonar-project.properties', "a")
            project_key = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(20))
            f.write("sonar.projectKey = " + project_key + "\n")
            f.write("sonar.projectName = " + project + "\n")
            f.write("sonar.report.export.path = " + project_key + ".json" + "\n")
            f.write("sonar.host.url = http://" + ip + ":9000" + "\n")
            f.close()
        except Exception as e:
            print e
            os.system('rm -rf ' + URL.split("/")[-1].split('.')[0])
            message.delete()
            return False, str(e)
        
        try:
            scanner_path = os.environ.get('SONAR_RUNNER_HOME')
            prop_file = open(scanner_path + "/conf/sonar-scanner.properties", "a")
            prop_file.write("sonar.host.url = http://" + ip + ":9000" + "\n")
            prop_file.close()
        except Exception as e:
            print e
            os.system('rm -rf ' + URL.split("/")[-1].split('.')[0])
            message.delete()
            return False, str(e)
        
        #execute scan process
        try:
            if 
            os.system('cd ' + project + ' && sonar-scanner')
            os.system('cd ' + project + ' && cp .scannerwork/' + project_key + '.json ' + '../reports')
            os.system('rm -rf ' + project)
        except Exception as e:
            print e
            os.system('rm -rf ' + URL.split("/")[-1].split('.')[0])
            message.delete()
            return False, str(e)
        #while it executes successfully, return ip address and ID
        return True, project_key
    else:
        return False, "busy"


if __name__ == '__main__':
    session = boto3.Session(aws_access_key_id = mis_sqs_key, aws_secret_access_key = mis_sqs_secret, region_name = 'us-east-1')
    sqs = session.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName = sqs_queue_name)
    while True:
        messages = queue.receive_messages(MaxNumberOfMessages = 10, MessageAttributeNames=['Title'])
        for message in list(set(messages)):
            if message.message_attributes is not None and message.message_attributes.get('Title').get('StringValue') == "sonarqube":
                key = mis_sqs_secret[:16]
                data = ast.literal_eval(message.body)

                #decrypt the token message
                ct = codecs.decode(data['token'], 'hex')
                counter = Counter.new(32, prefix = ct[:12], initial_value = 0)
                token = AES.new(key, AES.MODE_CTR, counter = counter).decrypt(ct[16:])
                result, ID = code_scanner(data['giturl'], token, message)

                #once the scan finished
                if result:
                    try:
                        f = open(root + "reports/" + ID + ".json", "r")
                        report = json.loads(f.read())
                        f.close()
                        critical = 0
                        major = 0
                        minor = 0
                        blocker = 0
                        for entry in report["issues"]:
                            blocker += 1 if entry.get('severity') == "BLOCKER" else 0
                            critical += 1 if entry.get('severity') == "CRITICAL" else 0
                            major += 1 if entry.get('severity') == "MAJOR" else 0
                            minor += 1 if entry.get('severity') == "MINOR" else 0
                        total = len(report["issues"])
                        payload = data
                        payload['higherrors'] = blocker
                        payload['mediumerrors'] = critical
                        payload['lowerrors'] = major
                        payload['totalerrors'] = total
                        payload['codescan_report'] = report
                        master_pod = subprocess.Popen("printenv | grep MISDASHBOARD_PORT", shell = True, stdout = subprocess.PIPE).stdout.read()
                        master_add = master_pod.split('\n')[-2].split("=")[-1].replace("tcp", "http")
                        headers = {"Content-Type": "application/json"}
                        put = requests.put(master_add, headers = headers, data = json.dumps(payload))
                        if put.status_code == 200:
                            message.delete()
                        else:
                            print put.text
                    except Exception as e:
                        print e
                    

            else:
                time.sleep(1)
                continue

                

