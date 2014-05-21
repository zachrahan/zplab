'''
	Drew Sinha - Pincus Lab
	Incubator.py
	Updated:19 May 2014

	Generates an class that encapsulates all of the routines needed to interact with a Peiler incubator
'''

import serial
import datetime
import time
import re
import sys
import warnings

class Incubator:
	_port = None	# Port to access incubator (serial.Serial pySerial object)
	timeout= None	# Custom timeout for the serial port (int/float)
	writeTimeout = None		# Custom write timeout for the serial port (int/float)
	verbose = None	# Flag to display output messages (logical)
		
	def __init__(self, inPort=None, inTimeout=1, inWriteTimeout=1, inVerbose=False):
		# Check for valid assignment for Incubator port
		if inPort=None	# If no port, information provided, raise error
			raise RuntimeError('(Incubator.__init__()) No valid port supplied for incubator')
		elif isinstance(inPort, serial.Serial):		# If a Serial object, directly copy it
			self._port = inPort
		elif:	# Otherwise, assume some valid system reference for port is given and instantiate with default timeout values
			self._port = serial.Serial(port=inPort, baudrate=2400, timeout=0,writeTimeout=0)
		
		# Populate instance variables
		self.timeout = inTimeout
		self.writeTimeout = inWriteTimeout
		self.verbose = inVerbose
		
	def __str__(self):	# Used for output
		return 'Current Temp: %2.1f \r Current Timer: %s \r Current Mode: %s \r Current Target Temp: %2.1f \r Current Port: %d' % (self.getTemp(), self.getTimer(), self.getMode(), self.getTargetTemp(), self.port)
	
	def read_data(self):
		# Returns buffered data up to, but not including, carriage return lying in device (incubator) buffer
		# Because of issues with some of Serial's read/write functionality, this handles all the necessary buffering and blocking
		enter_time = datetime.datetime.now()	# Get current time for working with timeout and pre-allocate return variable
		outBuffer=b''
		while 1:	
			tempBuffer = self.port.read(1)	# Read next character in device buffer
			if tempBuffer:  # If the device buffer is not empty
				outBuffer += tempBuffer
				for dummyNum in range(0, len(tempBuffer)):	# Keep reading from the buffer to get remainder of the data
					outBuffer += self.port.read(1)
				if outBuffer[len(outBuffer)-1]==ord('\r'):		# If we have reached the end of the message
					return outBuffer[:len(outBuffer)-1]	# Return buffer
			elif datetime.datetime.now() - enter_time > datetime.timedelta(seconds=self.timeout):	# If we timed out
				# Raise some warnings about timing out
				if len(outBuffer) > 0:
					warnings.warn('(Incubator.read_data()) Buffer read timed out with data still in buffer - %s' % outBuffer)
				else:
					warnings.warn('(Incubator.read_data()) Buffer read timed out with no data in buffer');
				return outBuffer	# Return the buffer
	
	def write_data(self,inMessage):
		# Writes data to device (incubator) then blocks for "timeout" seconds
		# Because of issues with some of Serial's read/write functionality, this handles all the necessary buffering and blocking
		self.port.write(inMessage)
		time.sleep(self.writeTimeout)
		print(datetime.datetime.now()-starttime)
	
	# Property for managing the port
	def getPort(self):
		return self._port	
	def setPort(self, inPort)
		self._port = inPort
		self._port.flush()	# Flush the port
		self._port.flushInput()
		self._port.flushOutput()
	port = property(getPort,setPort)
	
	# Interface functions for accessing/mutating incubator data	
		
	def getTemp(self):
		self.write_data('a\r'.encode('ascii'))		# Get current temp		
		templine = self.read_data()
		return float(templine)
	
	def getTimer(self):
		self.write_data('b\r'.encode('ascii'))		# Get current timer		
		templine = self.read_data().decode('ascii')
		templine = re.match('(\d\d):(\d\d):(\d\d)',templine)	# Use a regular expression to extract digits from returned data
		return datetime.timedelta(hours=int(templine.group(1)),minutes=int(templine.group(2)),seconds=int(templine.group(3)))
	
	def setTimer(self,inTimer):
		'''
			Accepts three formats:
				- String in the form of (H)H(:)MM(:)SS - e.g. '1:01:01'
				- 'timedelta' object
				- Integer that gives number of seconds to run the timer for
		'''
		
		if not inTimer: # If no value provided, raise exception
			raise AttributeError('(Incubator.setTimer()) No value provided for timer')
		elif isinstance(inTimer, str):	# If it's a string,
			result_match = re.match('(\d+)[:]?(\d+)[:]?(\d+)', inTimer)
			result=''
			for idx in range(1,4):
				result+=result_match.group(idx)
			if len(result) % 2 == 1: # If the string only has one hour character
				result = '0'+result
			self.write_data(('B '+''.join(result)+'\r').encode('ascii'))	# Send to device
			result = self.read_data()	# and read to make sure we don't have an error
			if(result.decode('ascii') != 'Command OK'):	# If command is not set successfully
				raise RuntimeError('(Incubator.setTimer()) Command not successful')
			elif verbose:
				print('(Incubator.setTimer()) Command Successful')
		elif isinstance(inTimer, (int,datetime.timedelta)):  # If integer or time delta object,
			# If we are passed a 'timedelta' object, convert it into number of seconds
			if(isinstance(inTimer,datetime.timedelta)):
				inTimer = inTimer.total_seconds()
			# Build the string sequentially 
			tempStr = ''	# Buffer for string to be passed to incubator
			tempTimer = inTimer	# Copy original value into temporary variable
			for ii in range(0,2):	# For minutes and seconds
				tempStr = str(tempTimer % 60)+tempStr	# Use mod to get the value and add to string
				if(tempTimer < 10):	# If the amount of time is in the single digit
					tempStr = '0'+tempStr	# Pad with an extra zero
				tempTimer = int((tempTimer+2*sys.float_info.epsilon)/60)	# Move on to next time unit by dividing by 60 and truncating (adding epsilon here to prevent aberrant truncation
			tempStr = str(tempTimer)+tempStr	# Finally, add on hours here
			if(tempTimer < 10):
				tempStr = '0'+tempStr
			self.write_data(('B '+tempStr+'\r').encode('ascii'))
			result = self.read_data()
			if(result.decode('ascii') != 'Command OK'):	# If command is not set successfully
				raise RuntimeError('(Incubator.setTimer()) Command not successful')
			elif verbose:
				print('(Incubator.setTimer()) Command Successful')
	
	def getMode(self):
		self.write_data('c\r'.encode('ascii'))		# Get auto mode status
		templine = self.read_data().decode('ascii')
		templine = re.match('^Auto (\S+)$',templine)
		return templine.group(1)
		
	def setMode(self,inMode):
		if not inMode: # If no value provided, raise exception
			raise AttributeError('(Incubator.setMode()) No value provided for mode')
		elif inMode.upper() != 'ON' and inMode.upper() != 'OFF':
			raise AttributeError('(Incubator.setMode()) Invalid value provided for mode')
		else:
			self.write_data(('C '+ inMode +'\r').encode('ascii'))
			result = self.read_data()
			if(result.decode('ascii') != 'Command OK'):	# If command is not set successfully
				raise RuntimeError('(Incubator.setMode()) Command not successful')
			elif verbose:
				print('(Incubator.setMode()) Command Successful')
	
	def getTargetTemp(self):
		self.write_data('d\r'.encode('ascii'))		# Get target temperature
		templine = self.read_data().decode('ascii')
		if(len(templine) > 10):	#Error message for no set target
			raise Warning('(Incubator.update()) No target temperature set on incubator')
			return []
		else:	# Take string, convert it to float, and then truncate and divide to get precision to tenth of a degree
			return int(float(templine)*1000)/1000
			
	def setTargetTemp(self,inTemp):
		if not inTemp: # If no value provided, raise exception
			raise AttributeError('(Incubator.setTargetTemp()) No value provided for timer')
		else:
			self.write_data(('A '+ ('%2.1f' % inTemp) + '\r').encode('ascii'))
			result = self.read_data()
			if(result.decode('ascii') != 'Command OK'):	# If command is not set successfully
				raise RuntimeError('(Incubator.setTargetTemp()) Command not successful')
			elif verbose:
				print('(Incubator.setTargetTemp()) Command Successful')

	def setDisplayIndicator(self,inDisplay):	
		# Sets Incubator display indicator to either temperature or timer
		# Accepts:	inDispay - String with value either 'temp' or 'timer'
		
		if not inDisplay:	# If the given display is empty
			raise RunTimeError('(Incubator.setDisplayIndicator()) No display mode provided')
		elif inDisplay.lower() == 'temp'.lower():	# If user wishes to display temperature
			self.write_data(('D \r').encode('ascii'))
		elif inDisplay.lower() == 'timer'.lower():	# If user wishes to display timer
			self.write_data(('E \r').encode('ascii'))
		
		result = self.read_data()
		if(result.decode('ascii') != 'Command OK'):	# If command is not set successfully
			raise RuntimeError('(Incubator.setMode()) Command not successful')
		elif verbose:
			print('(Incubator.setMode()) Command Successful')
