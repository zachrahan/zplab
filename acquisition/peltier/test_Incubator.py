import Incubator
import datetime

test = Incubator.Incubator('/dev/ttyUSB0',1)

try:
	test.setTargetTemp(24) #good
	print('1')
	test.setTimer(datetime.timedelta(seconds=3600)) #good
	print('2')
	test.setTimer('1:01:01') #good
	print('3')
	test.setTimer(3602) #good
	print('4')
	test.setMode('ON') #good
	print('5')
	test.setDisplayIndicator('temp') #good
	print('done')
except Exception as e:
	print(e)
