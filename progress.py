# https://medium.com/swlh/build-web-server-from-scratch-with-python-60188f3b162a

import socket
from threading import Thread
from time import time, strftime, sleep, localtime, gmtime
import webbrowser
from phaenotyp import basics

class http:
	active = False
	Thread_hosting = None

	start = b'''\
	HTTP/1.1 200 OK

	<html>
	'''

	refresh = b'''\
	<meta http-equiv="refresh" content="1">
	'''

	head = b'''\
	<head>
	<title>
	Phaenotyp | Progress
	</title>
	'''

	style = b'''\
	<style>
	* {font-family: sans-serif;}
	a:link {color: rgb(0, 0, 0); background-color: transparent; text-decoration: none;}
	a:visited {color: rgb(0,0,0); background-color: transparent; text-decoration: none;}
	a:hover {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}
	a:active {color: rgb(0,0,0); background-color: transparent; text-decoration: underline;}
	</style>
	'''

	headline = b'''\
	Phaenotyp | Progress <br>
	<br>
	'''

	@staticmethod
	def table_text(first, third):
		text = '<table>'
		text += '<tr>'

		# first column
		text += '<td style="width:100px">'
		text += '<p align="right">' + str(first) + '</p>'
		text += '</td>'

		# second
		text += '<td style="width:200px">'
		text += '<p align="right"></p>'
		text += '</td>'

		# third
		text += '<td style="width:200px">'
		text += '<p align="right">' + str(third) + '</p>'
		text += '</td>'

		text += '</tr>'
		text += '</table>'

		return text.encode()

	@staticmethod
	def hosting():
		http.started = time()
		http.started_text = strftime("%Y-%m-%d | %H:%M:%S")

		host, port = '', 8888

		listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		listen_socket.bind((host, port))
		listen_socket.listen(1)

		# show http
		while http.active:
			client_connection, client_address = listen_socket.accept()
			request_data = client_connection.recv(1024)

			# looks like this is necessary with threading?
			client_connection.send(b'HTTP/1.0 200 OK')
			client_connection.sendall(http.start)
			client_connection.sendall(http.refresh)
			client_connection.sendall(http.style)
			client_connection.sendall(http.headline)

			# tables
			jobs_total = str(basics.jobs_total)
			jobs_percentage = str(int(basics.jobs_percentage)) + " %"
			time_started = strftime("%H:%M:%S", localtime(basics.time_started))
			time_elapsed = strftime("%H:%M:%S", gmtime(basics.time_elapsed))
			time_left = strftime("%H:%M:%S", gmtime(basics.time_left))
	
			client_connection.sendall(http.table_text("jobs_total:", jobs_total))
			client_connection.sendall(http.table_text("jobs_percentage:", jobs_percentage))
			client_connection.sendall(http.table_text("time_started:", time_started))
			client_connection.sendall(http.table_text("time_elapsed:", time_elapsed))
			client_connection.sendall(http.table_text("time_left:", time_left))

			client_connection.close()
			sleep(0.1)

def run():
	http.active = True
	Thread_hosting = Thread(target=http.hosting)
	http.Thread_hosting = Thread_hosting
	Thread_hosting.start()
	webbrowser.open("http://127.0.0.1:8888/")
