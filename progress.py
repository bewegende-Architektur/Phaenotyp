# based on:
# https://medium.com/swlh/build-web-server-from-scratch-with-python-60188f3b162a

import bpy
import socket
from threading import Thread
from time import time, strftime, sleep, localtime, gmtime
import webbrowser
from phaenotyp import basics

class http:
	active = False
	server = None
	address = None
	
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
	def show_address():
		text = '<p>You can access this side in your local network via:<br>'
		text += http.address + '</p>'
		text += 'Make sure the port is open.</p>'
		text += '<br>'
		
		return text.encode()

	@staticmethod
	def show_terminal():
		text = '<p>'
		for line in basics.terminal:
			text += str(line) + '<br>'
		text += '</p>'
		text += '<br>'
		return text.encode()
		
	@staticmethod
	def table_text(first, second):
		text = '<table>'
		text += '<tr>'

		# first column
		text += '<td style="width:150">'
		text += '<p align="left">' + str(first) + '</p>'
		text += '</td>'

		# second
		text += '<td style="width:100">'
		text += '<p align="right">' + str(second) + '</p>'
		text += '</td>'

		text += '</tr>'
		text += '</table>'

		return text.encode()

	@staticmethod
	def setup():
		try:
			host, port = '', 8888
			
			# only to get ip
			import socket
			listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			listen_socket.connect(("8.8.8.8", 8888))
			http.address = str(listen_socket.getsockname()[0]) + ":" + str(port)
			listen_socket.close()
			
			# start to access local or in network
			listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			listen_socket.bind((host, port))
			listen_socket.setblocking(0)
			listen_socket.listen(1)			
			http.server = listen_socket
			except Exception:
				basics.log_exception("webinterface setup failed")
	
	@staticmethod
	def hosting():
		try:
			listen_socket = http.server
			
			# show http
			client_connection, client_address = listen_socket.accept()
			request_data = client_connection.recv(1024)

			# looks like this is necessary with threading?
			client_connection.send(b'HTTP/1.0 200 OK')
			client_connection.sendall(http.start)
			client_connection.sendall(http.refresh)
			client_connection.sendall(http.style)
			client_connection.sendall(http.headline)
			
			# show ip and port
			client_connection.sendall(http.show_address())
			
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
			
			# show terminal
			client_connection.sendall(http.show_terminal())
			
			client_connection.close()
		except Exception:
			basics.log_exception("webinterface hosting failed")
def run():
	http.active = True
	bpy.ops.wm.phaenotyp_webinterface()
	webbrowser.open("http://127.0.0.1:8888/")
