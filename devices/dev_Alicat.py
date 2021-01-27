# Licence: GNU General Public License version 2 (GPLv2)
# (C) 2019-2021 Matthias H. Richter

# Alicat Flow Controller & Meters, Pressure Controllers & Meters
# https://www.alicat.com
# https://documents.alicat.com/Alicat-Serial-Primer.pdf

from PyQt5.QtCore import QThread
import pyvisa
import time

class driver_Alicat(QThread):

    def __init__(self, config):
        QThread.__init__(self)
        self.port = config['dev_port']
        self.deviceid = config['dev_id']
        self.devicetype = config['dev_type'] # 1: controller, 2: meter(, 3: pressure)
        self.retry = config['dev_retry']
        self.Tretry = config['dev_Tretry']
        self.Tdriver = config['dev_Tdriver']
        self.savefilename = [config['dev_savefile']]
        self.readtime = 0
        self.runstate=False


        value = True
        while value:
            if config['dev_interface'] == 'RS232':
                # just using COMX does not always work
                self.visaport = 'ASRL%s::INSTR' % self.port[3:]
            try:
                rm = pyvisa.ResourceManager()
                self.inst = rm.open_resource(self.visaport)
                if config['dev_interface'] == 'RS232':
                    self.inst.baud_rate = config['dev_baudrate']
                self.inst.read_termination = '\r'
                self.inst.write_termination = '\r'
                print(' ... Alicat connected ...')
                value = False
            except Exception:
                print('Serial Error Alicat ...')
                if self.retry:
                    print(' ... trying again in a few seconds ...')
                    time.sleep(self.Tretry)
                    value = True
                else:
                    self.error = 1
                    value = False

        self.keys = ['pressure', 'temperature', 'volumetric_flow', 'mass_flow','setpoint', 'gas']
        self.gases = ['Air', 'Ar', 'CH4', 'CO', 'CO2', 'C2H6', 'H2', 'He',
                      'N2', 'N2O', 'Ne', 'O2', 'C3H8', 'n-C4H10', 'C2H2',
                      'C2H4', 'i-C2H10', 'Kr', 'Xe', 'SF6', 'C-25', 'C-10',
                      'C-8', 'C-2', 'C-75', 'A-75', 'A-25', 'A1025', 'Star29',
                      'P-5']        
        self.ready = 0
        self.error = 0
        self.setP = [0.0 for i in range(len(self.deviceid))]
        self.setPnew = [0.0 for i in range(len(self.deviceid))]
        self.save = [False for i in range(len(self.deviceid))]
        self.setG = [0.0 for i in range(len(self.deviceid))]
        self.setGnew = [0.0 for i in range(len(self.deviceid))]
        self.val = [0.0 for i in range(len(self.deviceid))]
        self.valpressure = [0.0 for i in range(len(self.deviceid))]
        # get first reading to populate the init values in the GUI
        self.getreading()
        for deviceidx, tmpvalue in enumerate(self.deviceid):
            self.setPnew[deviceidx] = self.setP[deviceidx]
            self.setGnew[deviceidx] = self.setG[deviceidx]


    def getreading(self):
        for deviceidx, tmpvalue in enumerate(self.deviceid):
                tmp = self.readAlicat(self.deviceid[deviceidx])
                if self.devicetype[deviceidx] == 1: # flowcontroller
                    if (len(tmp)==7):
                        self.valpressure[deviceidx] = float(tmp[1])
                        self.val[deviceidx] = float(tmp[4])
                        self.setP[deviceidx] = float(tmp[5])
                        if(self.save[deviceidx]):
                            try:
                                with open(self.savefilename[deviceidx],"a") as file_a:
                                    file_a.write(str(self.readtime)+','+str(tmp[0])+','+str(tmp[1])+','+str(tmp[2])+','+str(tmp[3])+','+str(tmp[4])+','+str(tmp[5])+','+str(tmp[6])+'\n')
                                file_a.close
                            except Exception:
                                self.error = 1
                                self.save[deviceidx] = False
                        try:
                            self.setG[deviceidx] = self.gases.index(tmp[6])
                        except Exception:
                            self.error = 1
                elif self.devicetype[deviceidx] == 2: # flowmeter
                    if (len(tmp)==6):
                        self.val[deviceidx] = float(tmp[4])
                        self.valpressure[deviceidx] = float(tmp[1])
                        if(self.save[deviceidx]):
                            try:
                                with open(self.savefilename[deviceidx],"a") as file_a:
                                    file_a.write(str(self.readtime)+','+str(tmp[0])+','+str(tmp[1])+','+str(tmp[2])+','+str(tmp[3])+','+str(tmp[4])+','+str(tmp[5])+'\n')
                                file_a.close
                            except Exception:
                                self.error = 1
                                self.save[deviceidx] = False
                        try:
                            self.setG[deviceidx] = self.gases.index(tmp[5])
                        except Exception:
                            self.error = 1


    def setvalues(self):
        for deviceidx, tmpvalue in enumerate(self.deviceid):
            if self.devicetype[deviceidx] == 1: # flowcontroller
                # set setpoint
                if (self.setPnew[deviceidx]!=self.setP[deviceidx]):
                    _ = self.inst.query(self.deviceid[deviceidx]+"S"+str(self.setPnew[deviceidx]))
            #elif self.devicetype == 2: # flowmeter
            # set gas types
            if (self.setGnew[deviceidx]!=self.setG[deviceidx]):
                _ = self.inst.query(self.deviceid[deviceidx]+"G"+str(self.setGnew[deviceidx]))


    def readAlicat(self,deviceid):
        return self.inst.query(deviceid).rstrip().split()


    def __del__(self):
        if self.ready !=0:
            self.stop()
            self.wait()


    def stop(self):
        self.runstate=False
        time.sleep(self.Tdriver)
        while(self.ready !=0):
            print(' ... waiting for shutdown')
            time.sleep(0.1)


    def run(self):
        self.runstate=True
        while self.runstate:
            self.getreading()
            self.setvalues()
            self.ready = 1
            time.sleep(self.Tdriver)
        self.ready = 0
