from sqlalchemy import create_engine

import mysql.connector
import pandas as pd



class EFDParameters():
    """Holds all parameters for the EFDReader.

    The EFDReader may have multiple databased that we wish to connect to. Some
    of these parameters are static and may rarely change, such as the IP address
    for a database. Parameters such as these are placed into the EFDParameters
    class. 

    Attributes
    ----------
    TEST_HOST : str
        The IP to the test EFD, currently in Daves office.
    TEST_DB : str
        Database name of the test EFD.
    TEST_USER : str
        User name of the test EFD.
    TEST_PW : str
        Password of the test EFD database. 
    """
    def __init__(self):

        # The Test EFD resides in Daves office. 
        self.TEST_HOST = "140.252.32.246"
        self.TEST_DB = "EFD"
        self.TEST_USER = "efduser"
        self.TEST_PW = "lssttest"

        #TODO: obtain info for the Simulation Cluser. 
        # self.SIMULATION_CLUSTER_HOST = 
        # self.SIMULATION_CLUSTER_DB =
        # self.SIMULATION_CLUSTER_USER = 
        # self.SIMULATION_CLUSTER_PW =

        #TODO: Dave tells me there are two EFD databases, get the info for it.
        # self.FOO_HOST = 
        # self.FOO_DB = 
        # self.FOO_USER = 
        # self.FOO_PW =  


class EFDReader():
    """Manages a data structure populated by the EFD.

    The EFDReader connects to the EFD, populates a data structure with data from
    the EFD and updates the data structure. The EFDReader, despite the EFD being
    a MySQL database is also capable of connecting to SQL databases. 

    Attributes
    ----------
    parameters : lsst.ts.scheduler.EFDParameters()
        Class that contains the parameters to various EFD databases. 
    efd_telemetry : dict
        Data structure to hold data retrieved from the EFD. 
    """
    def __init__(self, efd_telemetry=None, max_reconnection_attempts=None): 
        """Initialize EFDReader & relevent objects.

        Parameters
        ----------
        efd_telemetry : dict
            A passed dictionary to populate data from the EFD with.
        max_reconnection_attempts : int
            Maximum amount of reconnection attempts that can be made before
            raising an exception. The count only starts after an initial
            successful attempt. 
        """ 
        self.parameters = EFDParameters()
        
        if efd_telemetry == None:
            self.efd_telemetry = {}

        if not isinstance(self.efd_telemetry, dict):
            raise ValueError("efd_telemetry must be of type dictionary") 

    def connect_to_db(self):
        """Connects to database currently connecting to default.

        """
        host = self.parameters.TEST_HOST
        db = self.parameters.TEST_DB
        user = self.parameters.TEST_USER
        pw = self.parameters.TEST_PW

        db_connection = mysql.connector.connect(host=host, database=db, 
                                                user=user, password=pw)

        df = pd.read_sql_query("SELECT * FROM scheduler_target", db_connection)        



    def update_efd_telemetry(self):
        pass
