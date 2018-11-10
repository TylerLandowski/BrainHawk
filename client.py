# -*- coding: utf-8 -*-

"""
@author: Tyler Landowski
"""

import socket as s
#from enum import Enum


class BizHawkTCPClient:
	# class Type(Enum):
	# 	STRING = "STR"
	# 	NUM = "NUM"

	bufsize = 1024  # Size of message buffer

	def __init__(self, ip = "127.0.0.1", port = 1337):
		self.server_ip = ip
		self.server_port = port
		self.client = None
		self.start()

	def start(self):
		# Create a IPV4 (AF_INET) socket object. Use TCP protocol (SOCK_STREAM)
		self.client = s.socket(s.AF_INET, s.SOCK_STREAM)
		self.client.connect(('127.0.0.1', 1337))

	def close(self):
		self.client.close()

	def send_str(self, msg):
		self.client.send(msg.encode())
		return self.client.recv(self.bufsize)

	def set(self, var, data_type, val):
		return self.send_str("SET " + var + " " + data_type + " " + str(val))

	def get(self, var):
		return self.send_str("GET " + var)


client = BizHawkTCPClient()

print((client.get('x')).decode())
#print(client.get("screenshot5").decode())

client.close()
