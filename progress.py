# https://medium.com/swlh/build-web-server-from-scratch-with-python-60188f3b162a

import socket
from threading import Thread
from time import time, strftime, sleep
import webbrowser

class http:
	active = True
	Thread_hosting = None

	started = None
	started_text = None

	p, c, i, g, o = [0,0], [0,0], [0,0], [0,0], [0,0]

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
	def update_p():
		http.p[0] += 1

	@staticmethod
	def update_c():
		http.c[0] += 1

	@staticmethod
	def update_i():
		http.i[0] += 1

	@staticmethod
	def update_o():
		http.o[0] += 1

	@staticmethod
	def update_g():
		http.g[0] += 1

	@staticmethod
	def reset_pci(end):
		http.p = [0, end]
		http.c = [0, end]
		http.i = [0, end]

	@staticmethod
	def reset_o(end):
		http.o = [0, end]

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
	def table_http(first, n_of_x):
		text = '<table>'
		text += '<tr>'

		# first column
		text += '<td style="width:100px">'
		text += '<p align="right">' + str(first) + '</p>'
		text += '</td>'

		# second
		output = ""
		if n_of_x[1] != 0:
			amount = int(10/n_of_x[1]*n_of_x[0])
			for i in range(amount):
				output += "&#9608;"

		text += '<td style="width:200px">'
		text += '<p align="left">' + str(output) + '</p>'
		text += '</td>'

		# third
		output = str(n_of_x[0]) + " | " + str(n_of_x[1])
		text += '<td style="width:200px">'
		text += '<p align="right">' + output + '</p>'
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
			client_connection.sendall(http.table_text("started:", http.started_text))

			# https://stackoverflow.com/questions/27779677/how-to-format-elapsed-time-from-seconds-to-hours-minutes-seconds-and-milliseco
			hours, rem = divmod(time() - http.started, 3600)
			minutes, seconds = divmod(rem, 60)
			elapsed = "{:0>2}:{:0>2}:{:0>2}".format(int(hours), int(minutes), int(seconds))
			client_connection.sendall(http.table_text("elapsed:", elapsed))

			client_connection.send(b'<br>')
			client_connection.sendall(http.table_http("prepare:", http.p))
			client_connection.sendall(http.table_http("calculate:", http.c))
			client_connection.sendall(http.table_http("interweave:", http.i))

			client_connection.send(b'<br>')
			client_connection.sendall(http.table_http("optimization:", http.o))
			
			# to show only with ga
			if http.g[1] > 0:
				client_connection.send(b'<br>')
				client_connection.sendall(http.table_http("generation:", http.g))

			client_connection.close()

		# done - go back to blender
		client_connection, client_address = listen_socket.accept()
		request_data = client_connection.recv(1024)

		# looks like this is necessary with threading?
		client_connection.send(b'HTTP/1.0 200 OK')
		client_connection.sendall(http.start)
		client_connection.sendall(http.style)
		client_connection.sendall(http.headline)

		# tables
		client_connection.sendall(http.table_text("started:", http.started_text))

		# https://stackoverflow.com/questions/27779677/how-to-format-elapsed-time-from-seconds-to-hours-minutes-seconds-and-milliseco
		hours, rem = divmod(time() - http.started, 3600)
		minutes, seconds = divmod(rem, 60)
		elapsed = "{:0>2}:{:0>2}:{:0>2}".format(int(hours), int(minutes), int(seconds))
		client_connection.sendall(http.table_text("elapsed:", elapsed))
		client_connection.sendall(b"<br>")

		http_response = b"""\
		done
		</html>
		"""
		client_connection.sendall(http_response)
		client_connection.close()
		sleep(0.1)

def run():
	http.active = True
	http.p = [0, 0]
	http.c = [0, 0]
	http.i = [0, 0]

	http.o = [0, 0]
	http.g = [0, 0]

	Thread_hosting = Thread(target=http.hosting)
	http.Thread_hosting = Thread_hosting
	Thread_hosting.start()
	webbrowser.open("http://127.0.0.1:8888/")
