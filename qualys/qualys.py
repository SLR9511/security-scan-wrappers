from requests.auth import HTTPBasicAuth
import requests
import xmltodict, json
import ast
import time
from multiprocessing import Process
import boto3
import os

auth = HTTPBasicAuth(username, password)
option_title = option
ip_network_id = network_id
iscanner_name = scanner_name


mis_sqs_secret = os.environ.get('MIS_SQS_SECRET')
mis_sqs_key = os.environ.get('MIS_SQS_KEY')
sqs_queue_name = queue_name
session_sqs = boto3.Session(aws_access_key_id = mis_sqs_key, aws_secret_access_key = mis_sqs_secret, region_name = 'us-east-1')
sqs = session_sqs.resource('sqs')
queue = sqs.get_queue_by_name(QueueName = sqs_queue_name)


bucket_name = bucket
mis_s3_secret = os.environ.get('MIS_S3_SECRET')
mis_s3_key = os.environ.get('MIS_S3_KEY')
session_s3 = boto3.Session(aws_access_key_id = mis_s3_key, aws_secret_access_key = mis_s3_secret, region_name = 'us-east-1')
s3 = session_s3.resource('s3')
bucket = s3.Bucket(bucket_name)

def qualys_scan(ip, project, version,message):
	try:
		index = project + version
		print "Launch scan for " + index
		#launch scan
		url_scan = "https://qualysapi.qualys.com/api/2.0/fo/scan/"
		params_scan = {'action': 'launch', 'option_title': option_title, ' ip_network_id': ip_network_id, 'iscanner_name': iscanner_name}
		params_scan['ip'] = ip
		params_scan['scan_title'] = "scan_" + index
		header_scan = {'X-Requested-With': 'Curl'}
		scan = requests.post(url_scan, auth = auth, params = params_scan, headers = header_scan)
		scan_response = json.loads(json.dumps(xmltodict.parse(scan.text)))
		print scan_response['SIMPLE_RETURN']['RESPONSE']['ITEM_LIST']['ITEM']
		for item in scan_response['SIMPLE_RETURN']['RESPONSE']['ITEM_LIST']['ITEM']:
			if item['KEY'] == 'REFERENCE':
				scan_ID = item['VALUE']
				print scan_ID
		
		#get scan status and wait it finish
		time.sleep(2)
		params_scan_status = {'action': 'list'}
		params_scan_status['scan_ref'] = scan_ID
		scan_status_cmd = requests.get(url_scan, auth = auth, params = params_scan_status, headers = header_scan)
		scan_status_response = json.loads(json.dumps(xmltodict.parse(scan_status_cmd.text)))
		scan_status = scan_status_response['SCAN_LIST_OUTPUT']['RESPONSE']['SCAN_LIST']['SCAN']['STATUS']['STATE']
		print index + scan_status
		while scan_status != 'Finished':
			time.sleep(60)
			scan_status_cmd = requests.get(url_scan, auth = auth, params = params_scan_status, headers = header_scan)
			scan_status_response = json.loads(json.dumps(xmltodict.parse(scan_status_cmd.text)))
			scan_status = scan_status_response['SCAN_LIST_OUTPUT']['RESPONSE']['SCAN_LIST']['SCAN']['STATUS']['STATE']
			print index + scan_status
		print index + " scan finished, starting to get reports..."

		#when scan finished, launch report, here we need pdf and csv these two formats
		#csv
		print "Waiting CSV report for " + index
		url_report = "https://qualysapi.qualys.com/api/2.0/fo/report/"
		params_report_csv = {'action': 'launch', 'template_id': '2609020', 'report_type': 'Scan', 'output_format': 'csv'}
		params_report_csv['report_refs'] = scan_ID
		params_report_csv['report_title'] = "report_" + index
		header_report = {'X-Requested-With': 'Curl Sample'}
		report_csv = requests.post(url_report, auth = auth, params = params_report_csv, headers = header_report)
		report_csv_response = json.loads(json.dumps(xmltodict.parse(report_csv.text)))
	 
		csv_ID = report_csv_response['SIMPLE_RETURN']['RESPONSE']['ITEM_LIST']['ITEM']['VALUE']
		
		#wait csv report finish
		params_query_csv = {'action': 'list'}
		params_query_csv['id'] = csv_ID
		query_csv = requests.get(url_report, auth = auth, params = params_query_csv, headers = header_report)
		query_csv_response = json.loads(json.dumps(xmltodict.parse(query_csv.text)))
		
		while True:
			try:
				query_csv = requests.get(url_report, auth = auth, params = params_query_csv, headers = header_report)
				query_csv_response = json.loads(json.dumps(xmltodict.parse(query_csv.text)))
				status_csv = query_csv_response['REPORT_LIST_OUTPUT']['RESPONSE']['REPORT_LIST']['REPORT']['STATUS']['STATE']
				break
			except Exception as e:
				time.sleep(2)
		
		print index + status_csv
		while status_csv != 'Finished':
			time.sleep(10)
			query_csv = requests.get(url_report, auth = auth, params = params_query_csv, headers = header_report)
			query_csv_response = json.loads(json.dumps(xmltodict.parse(query_csv.text)))
			status_csv = query_csv_response['REPORT_LIST_OUTPUT']['RESPONSE']['REPORT_LIST']['REPORT']['STATUS']['STATE']
			print index + status_csv
		
		#when csv rpeort finished, download it 
		params_download_csv = {'action': 'fetch'}
		params_download_csv['id'] = csv_ID
		download_csv = requests.get(url_report, auth = auth, params = params_download_csv, headers = header_report)
		report_csv = download_csv.content
		f_csv = open('report_' + index + '.csv', 'wb')
		f_csv.write(report_csv)
		f_csv.close()
		print "CSV for " + index + " downloaded!!"
		
		#PDF
		print "Waiting PDF report for " + index
		params_report_pdf = {'action': 'launch', 'template_id': '2609020', 'report_type': 'Scan', 'output_format': 'pdf'}
		params_report_pdf['report_refs'] = scan_ID
		params_report_pdf['report_title'] = "report_" + index
		header_report = {'X-Requested-With': 'Curl Sample'}
		report_pdf = requests.post(url_report, auth = auth, params = params_report_pdf, headers = header_report)
		report_pdf_response = json.loads(json.dumps(xmltodict.parse(report_pdf.text)))
		
	 
		pdf_ID = report_pdf_response['SIMPLE_RETURN']['RESPONSE']['ITEM_LIST']['ITEM']['VALUE']
		
		#wait pdf report finish
		time.sleep(2)
		params_query_pdf = {'action': 'list'}
		params_query_pdf['id'] = pdf_ID
		query_pdf = requests.get(url_report, auth = auth, params = params_query_pdf, headers = header_report)
		query_pdf_response = json.loads(json.dumps(xmltodict.parse(query_pdf.text)))

		while True:
			try:
				query_pdf = requests.get(url_report, auth = auth, params = params_query_pdf, headers = header_report)
				query_pdf_response = json.loads(json.dumps(xmltodict.parse(query_pdf.text)))
				status_pdf = query_pdf_response['REPORT_LIST_OUTPUT']['RESPONSE']['REPORT_LIST']['REPORT']['STATUS']['STATE']
				break
			except Exception as e:
				time.sleep(2)

		print index + status_pdf
		while status_pdf != 'Finished':
			time.sleep(10)
			query_pdf = requests.get(url_report, auth = auth, params = params_query_pdf, headers = header_report)
			query_pdf_response = json.loads(json.dumps(xmltodict.parse(query_pdf.text)))
			status_pdf = query_pdf_response['REPORT_LIST_OUTPUT']['RESPONSE']['REPORT_LIST']['REPORT']['STATUS']['STATE']
			print index + status_pdf
		
		#when pdf rpeort finished, download it 
		params_download_pdf = {'action': 'fetch'}
		params_download_pdf['id'] = pdf_ID
		download_pdf = requests.get(url_report, auth = auth, params = params_download_pdf, headers = header_report)
		report_pdf = download_pdf.content
		f_pdf = open('report_' + index + '.pdf', 'wb')
		f_pdf.write(report_pdf)
		f_pdf.close()
		print "PDF for " + index + " downloaded!!"

		#once two reports finished, upload to S3
		
		file_csv = "report_" + index + ".csv"
		file_pdf = "report_" + index + ".pdf"

		project_name = index.split('_')[0]
		version = index.split('_')[1]
		directory = project_name + "/" + version + "/"

		bucket.upload_file(file_csv, directory + file_csv)
		bucket.upload_file(file_pdf, directory + file_pdf)

		#delete the message and return a new msg to main portal
		os.remove("report_" + index + ".csv")
		os.remove("report_" + index + ".pdf")
		message.delete()

		msg_body = "{\"projectname\": \"" + project + "\", \"releaseno\": " + version + ", \"path_for_report\": \"" + directory + file_csv +"\"}"
		response = queue.send_messages(
			Entries=[
			{
			'Id': 'string',
			'MessageBody': msg_body,
			'DelaySeconds': 0,
			'MessageAttributes': {
				'Title': {
					'StringValue': 'qualys_response',
					'DataType': 'String'
				}
			},
			'MessageDeduplicationId': 'string',
			'MessageGroupId': 'qualys'
			},
			]
		)

		print response
	except Exception as e:
		print str(e)
		msg_body = "{\"projectname\": \"" + project + "\", \"releaseno\": " + version + ", \"path_for_report\": \"null\", \"error\": \"" + str(e) + "\"}"
		response = queue.send_messages(
			Entries=[
			{
			'Id': 'string',
			'MessageBody': msg_body,
			'DelaySeconds': 0,
			'MessageAttributes': {
				'Title': {
					'StringValue': 'qualys_response',
					'DataType': 'String'
				}
			},
			'MessageDeduplicationId': 'string',
			'MessageGroupId': 'qualys'
			},
			]
		)
		print response
	
	



if __name__ == "__main__":
	
	while True:
		messages = queue.receive_messages(MaxNumberOfMessages = 10, MessageAttributeNames=['Title'])
		for message in list(set(messages)):
			print message.body
			if message.message_attributes is not None and message.message_attributes.get('Title').get('StringValue') == "qualys":
				data = ast.literal_eval(message.body)
				ips = data['params']
				project_name = data['projectname'] 
				version = str(data['releaseno'])
				p = Process(target = qualys_scan, args = (ips, project_name, version, message))
				p.start()
			else:
				time.sleep(2)
				print "no msg"

				
	
	


