#!/usr/bin/env python3
"""
NAME: lf_interop_port_reset_test.py

PURPOSE:The LANforge interop port reset test allows user to use lots of real Wi-Fi stations and connect them the AP
 under test and then disconnect and reconnect a random number of
stations at random intervals

EXAMPLE:
$ ./lf_interop_port_reset_test.py --host 192.168.1.31 --dut TestAp --ssid testssid --passwd testpass --encryp psk2
 --band 5G --clients 2 -- reset 10 --time_int 60

NOTES:
#Currently this script will forget all network and then apply batch modify on real devices connected to LANforge
and in the end generates report

"""

import sys
import os
import importlib
import argparse
import shlex
import subprocess
import json
import time
import datetime
from datetime import datetime
import pandas as pd

if sys.version_info[0] != 3:
    print("This script requires Python3")
    exit()
sys.path.append(os.path.join(os.path.abspath(__file__ + "../../../")))
interop_modify = importlib.import_module("py-scripts.lf_interop_modify")
lf_csv = importlib.import_module("py-scripts.lf_csv")
realm = importlib.import_module("py-json.realm")
Realm = realm.Realm
lf_report_pdf = importlib.import_module("py-scripts.lf_report")
lf_graph = importlib.import_module("py-scripts.lf_graph")


class InteropPortReset(Realm):
    def __init__(self, host,
                 dut=None,
                 ssid=None,
                 passwd=None,
                 encryp=None,
                 band=None,
                 clients=None,
                 reset=None,
                 time_int=None
                 ):
        super().__init__(lfclient_host=host,
                         lfclient_port=8080)
        self.adb_device_list = None
        self.host = host
        self.phn_name = []
        self.dut_name = dut
        self.ssid = ssid
        self.passwd = passwd
        self.encryp = encryp
        self.band = band
        self.clients = clients
        self.reset = reset
        self.time_int = time_int

    def get_device_details(self, query="name"):
        # query device related details like name, phantom, model name etc
        value = []
        cmd = '''curl -H 'Accept: application/json' http://''' + str(self.host) + ''':8080/adb/'''
        args = shlex.split(cmd)
        process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        output = (stdout.decode("utf-8"))
        out = json.loads(output)
        final = out["devices"]
        print("response", final)
        if type(final) == list:
            # print(len(final))
            keys_lst = []
            for i in range(len(final)):
                keys_lst.append(list(final[i].keys())[0])
            # print(keys_lst)

            for i, j in zip(range(len(keys_lst)), keys_lst):
                value.append(final[i][j][query])

        else:
            #  only one device is present
            value.append(final[query])
        return value

    def run(self):
        # start timer
        test_time = datetime.now()
        test_time = test_time.strftime("%b %d %H:%M:%S")
        print("Test started at ", test_time)

        # get the list of adb devices
        self.adb_device_list = self.get_device_details(query="name")
        print(self.adb_device_list)

        for i in range(len(self.adb_device_list)):
            self.phn_name.append(self.adb_device_list[i].split(".")[2])
        print("phn_name", self.phn_name)

        # check status of devices
        phantom = self.get_device_details(query="phantom")
        print(phantom)
        state = None
        for i in phantom:
            if str(i) == "False":
                print("device are up")
                state = "up"
            else:
                print("all devices are not up")
                exit(1)
        if state == "up":
            device_name = []

            # provide device name
            for i, j in zip(self.adb_device_list, range(len(self.adb_device_list))):
                device_name.append("device_" + str(int(j + 1)))
                modify = interop_modify.InteropCommands(_host=self.host,
                                                        _port=8080,
                                                        device_eid=i,
                                                        set_adb_user_name=True,
                                                        adb_username="device_" + str(int(j + 1)))

                modify.run()
            print("device name", device_name)

            print("connect all phones to a particular ssid")
            print("apply ssid using batch modify")
            for i, y in zip(self.adb_device_list, device_name):
                modify_2 = interop_modify.InteropCommands(_host=self.host,
                                                          _port=8080,
                                                          device_eid=i,
                                                          user_name=y,
                                                          mgr_ip=self.host,
                                                          ssid=self.ssid,
                                                          passwd=self.passwd,
                                                          crypt=self.encryp,
                                                          apply=True)
                modify_2.run()
            print("check heath data")
            health = dict.fromkeys(self.adb_device_list)
            print(health)

            for i in self.adb_device_list:

                modi = interop_modify.InteropCommands(_host=self.host,
                                                      _port=8080,
                                                      device_eid=i)
                dev_state = modi.get_device_state()
                print("device state", dev_state)
                if dev_state == "COMPLETED,":
                    print("phone is in connected state")
                    ssid = modi.get_device_ssid()
                    if ssid == self.ssid:
                        print("device is connected to expected ssid")
                        health[i] = modi.get_wifi_health_monitor(ssid=self.ssid)
                else:
                    print("wait for some time and check again")
                    time.sleep(120)
                    dev_state = modi.get_device_state()
                    print("device state", dev_state)
                    if dev_state == "COMPLETED,":
                        print("phone is in connected state")
                        ssid = modi.get_device_ssid()
                        if ssid == self.ssid:
                            print("device is connected to expected ssid")
                            health[i] = modi.get_wifi_health_monitor(ssid=self.ssid)
                    else:
                        print("device state", dev_state)
                        health[i] = {'ConnectAttempt': '0', 'ConnectFailure': '0', 'AssocRej': '0', 'AssocTimeout': '0'}
            print("health", health)

            reset_list = []
            for i in range(self.reset):
                reset_list.append(i)
            print("reset list", reset_list)
            reset_dict = dict.fromkeys(reset_list)

            # previous ki dict
            prev_dict = {}
            pre_heath = {}
            pre_con_atempt, prev_con_fail, prev_assrej, prev_asso_timeout = None, None, None, None

            for r, final in zip(range(self.reset), reset_dict):
                con_atempt, con_fail, assrej, asso_timeout = None, None, None, None
                print("r", r)
                for i, y in zip(self.adb_device_list, device_name):
                    # enable and disable Wi-Fi
                    print("disable wifi")
                    modify_1 = interop_modify.InteropCommands(_host=self.host,
                                                              _port=8080,
                                                              device_eid=i,
                                                              wifi="disable")
                    modify_1.run()

                    time.sleep(5)

                    print("enable wifi")
                    modify_3 = interop_modify.InteropCommands(_host=self.host,
                                                              _port=8080,
                                                              device_eid=i,
                                                              wifi="enable")
                    modify_3.run()
                health1 = dict.fromkeys(self.adb_device_list)
                in_dict_per_device = dict.fromkeys(self.adb_device_list)

                # print(in_dict_per_device)

                local_dict = dict.fromkeys(self.adb_device_list)
                val = ["pre_con_atempt", "prev_con_fail", "prev_assrej", "prev_asso_timeout"]
                for i in local_dict:
                    local_dict[i] = dict.fromkeys(val)
                # print("local dict", local_dict)
                for i, adb in zip(self.adb_device_list, in_dict_per_device):

                    value = ["ConnectAttempt", "ConnectFailure", "AssocRej", "AssocTimeout", "Connected"]
                    sub_dict = dict.fromkeys(value)
                    modi = interop_modify.InteropCommands(_host=self.host,
                                                          _port=8080,
                                                          device_eid=i)
                    dev_state = modi.get_device_state()
                    print("device state", dev_state)
                    if dev_state == "COMPLETED,":
                        print("phone is in connected state")
                        sub_dict["Connected"] = True
                        ssid = modi.get_device_ssid()
                        if ssid == self.ssid:
                            print("device is connected to expected ssid")
                            health1[i] = modi.get_wifi_health_monitor(ssid=self.ssid)
                    else:
                        print("wait for some time and check again")
                        time.sleep(120)
                        dev_state = modi.get_device_state()
                        print("device state", dev_state)
                        if dev_state == "COMPLETED,":
                            print("phone is in connected state")
                            sub_dict["Connected"] = True
                            ssid = modi.get_device_ssid()
                            if ssid == self.ssid:
                                print("device is connected to expected ssid")
                                health1[i] = modi.get_wifi_health_monitor(ssid=self.ssid)
                        else:
                            print("device state", dev_state)
                            health1[i] = {'ConnectAttempt': '0', 'ConnectFailure': '0', 'AssocRej': '0',
                                          'AssocTimeout': '0'}
                            sub_dict["Connected"] = False
                    print("health1", health1)

                    if r == 0:
                        if int(health[i]['ConnectAttempt']) == 0:
                            con_atempt = 1
                        elif int(health1[i]['ConnectAttempt']) == 0:
                            con_atempt = 0
                        else:
                            con_atempt = int(health1[i]['ConnectAttempt']) - int(health[i]['ConnectAttempt'])

                        con_fail = int(health1[i]['ConnectFailure']) - int(health[i]['ConnectFailure'])
                        assrej = int(health1[i]['AssocRej']) - int(health[i]['AssocRej'])
                        asso_timeout = int(health1[i]['AssocTimeout']) - int(health[i]['AssocTimeout'])
                        # print(con_atempt, con_fail, assrej, asso_timeout)
                        local_dict[i]["pre_con_atempt"] = con_atempt
                        local_dict[i]["prev_con_fail"] = con_fail
                        local_dict[i]["prev_assrej"] = assrej
                        local_dict[i]["prev_asso_timeout"] = asso_timeout

                        pre_con_atempt, prev_con_fail, prev_assrej, prev_asso_timeout = con_atempt, con_fail, assrej, asso_timeout
                        # print("previous stage",  pre_con_atempt, prev_con_fail, prev_assrej, prev_asso_timeout)

                    else:
                        print("prev health", pre_heath)
                        if int(health1[i]['ConnectAttempt']) == 0:
                            con_atempt = 0
                        else:
                            if int(pre_heath[i]['ConnectAttempt']) == 0:
                                con_atempt = int(health1[i]['ConnectAttempt']) - int(health[i]['ConnectAttempt']) - int(
                                    prev_dict[i]["pre_con_atempt"])
                            else:
                                con_atempt = int(health1[i]['ConnectAttempt']) - int(pre_heath[i]['ConnectAttempt'])
                        local_dict[i]["pre_con_atempt"] = con_atempt

                        if int(health1[i]['ConnectFailure']) == 0:
                            con_fail = 0
                        else:
                            if pre_heath[i]['ConnectFailure'] == 0:
                                con_fail = int(health1[i]['ConnectFailure']) - int(health[i]['ConnectFailure']) - int(
                                    prev_dict[i]["prev_con_fail"])
                            else:
                                con_fail = int(health1[i]['ConnectFailure']) - int(pre_heath[i]['ConnectFailure'])
                        local_dict[i]["prev_con_fail"] = con_fail

                        if int(health1[i]['AssocRej']) == 0:
                            assrej = 0
                        else:
                            if pre_heath[i]['AssocRej'] == 0:
                                assrej = int(health1[i]['AssocRej']) - int(health[i]['AssocRej']) - int(
                                    prev_dict[i]["prev_assrej"])
                            else:
                                assrej = int(health1[i]['AssocRej']) - int(health1[i]['AssocRej'])
                        local_dict[i]["prev_assrej"] = assrej

                        if int(health1[i]['AssocTimeout']) == 0:
                            asso_timeout = 0
                        else:
                            if pre_heath[i]['AssocTimeout'] == 0:
                                asso_timeout = int(health1[i]['AssocTimeout']) - int(health[i]['AssocTimeout']) - int(
                                    prev_dict[i]["prev_asso_timeout"])
                            else:
                                asso_timeout = int(health1[i]['AssocTimeout']) - pre_heath[i]['AssocTimeout']
                        local_dict[i]["prev_asso_timeout"] = asso_timeout
                        pre_con_atempt, prev_con_fail, prev_assrej, prev_asso_timeout = con_atempt, con_fail, assrej, asso_timeout

                    sub_dict["ConnectAttempt"] = con_atempt
                    sub_dict["ConnectFailure"] = con_fail
                    sub_dict["AssocRej"] = assrej
                    sub_dict["AssocTimeout"] = asso_timeout
                    # print("sub dictionary", sub_dict)
                    in_dict_per_device[adb] = sub_dict
                    # print(in_dict_per_device)
                pre_heath = health1
                prev_dict = local_dict
                reset_dict[final] = in_dict_per_device
                print("provide time interval between every reset")
                time.sleep(self.time_int)

            print("reset dict", reset_dict)
            test_end = datetime.now()
            test_end = test_end.strftime("%b %d %H:%M:%S")
            print("Test ended at ", test_end)
            s1 = test_time
            s2 = test_end  # for example
            FMT = '%b %d %H:%M:%S'
            test_duration = datetime.strptime(s2, FMT) - datetime.strptime(s1, FMT)
            return reset_dict, test_duration

    def generate_per_station_graph(self, device_names=None, dataset=None, labels=None):

        # device_names = ['1.1.RZ8N70TVABP', '1.1.RZ8RA1053HJ']
        print("dataset", dataset)
        print(labels)
        print(device_names)
        # dataset = [[1, 1], [1, 1]]
        labels = ["Connected", "Disconnected"]
        graph = lf_graph.lf_bar_graph(_data_set=dataset, _xaxis_name="Device Name",
                                      _yaxis_name="Reset = " + str(self.reset),
                                      _xaxis_categories=device_names,
                                      _label=labels, _xticks_font=8,
                                      _graph_image_name="per_station_graph",
                                      _color=['g', 'r'], _color_edge='black',
                                      _figsize=(12, 4),
                                      _grp_title="Per station graph ",
                                      _xaxis_step=1,
                                      _show_bar_value=True,
                                      _text_font=6, _text_rotation=30,
                                      _legend_loc="upper right",
                                      _legend_box=(1, 1.15),
                                      _enable_csv=True
                                      )
        graph_png = graph.build_bar_graph()
        print("graph name {}".format(graph_png))
        return graph_png

    def generate_report(self, reset_dict=None, test_dur=None):
        report = lf_report_pdf.lf_report(_path="", _results_dir_name="Interop_port_reset_test",
                                         _output_html="port_reset_test.html",
                                         _output_pdf="port_reset_test.pdf")
        date = str(datetime.now()).split(",")[0].replace(" ", "-").split(".")[0]
        test_setup_info = {
            "DUT Name": self.dut_name,
            "SSID": self.ssid,
            "Test Duration": test_dur,
        }
        report.set_title("LANforge Interop Port Reset Test")
        report.set_date(date)
        report.build_banner()
        report.set_table_title("Test Setup Information")
        report.build_table_title()

        report.test_setup_table(value="Device under test", test_setup_data=test_setup_info)
        report.set_obj_html("Objective",
                            "The LANforge interop port reset test allows user to use lots of real WiFi stations and"
                            " connect them the AP under test and then disconnect and reconnect a random number of"
                            " stations at random intervals. The objective of this test is to "
                            "mimic a enterprise/large public venue scenario where a number of stations arrive,"
                            " connect and depart in quick succession. A successful test result would be that "
                            "AP remains stable over the duration of the test and that stations can continue to reconnect to the AP.")
        report.build_objective()
        user_name = self.get_device_details(query="user-name")
        print("user name", user_name)

        # data set logic
        conected_list = []
        disconnected_list = []
        for j in self.adb_device_list:
            # print(j)
            local = []
            local_2 = []
            for i in reset_dict:
                print(i)
                if j in list(reset_dict[i].keys()):
                    if reset_dict[i][j]['Connected']:
                        local.append("yes")
                    if reset_dict[i][j]['Connected']:
                        local_2.append("No")
                    else:
                        local_2.append("yes")
            conected_list.append(local)
            disconnected_list.append(local_2)
        # print(conected_list)
        # print(disconnected_list)

        # count connects and disconnects
        conects = []
        disconnects = []
        for i, y in zip(range(len(conected_list)), range(len(disconnected_list))):
            # print(i)
            x = conected_list[i].count("yes")
            conects.append(x)
            z = disconnected_list[y].count("yes")
            # print("z", z)
            disconnects.append(z)

        # print(conects)
        # print(disconnects)
        dataset = []
        dataset.append(conects)
        dataset.append(disconnects)
        # print(dataset)

        report.set_obj_html("Connection Graph",
                            "The below graph provides information regarding per station connection/disconnection count")
        report.build_objective()
        graph1 = self.generate_per_station_graph(device_names=self.adb_device_list, dataset=dataset)
        # graph1 = self.generate_per_station_graph()
        report.set_graph_image(graph1)
        report.set_csv_filename(graph1)
        report.move_csv_file()
        report.move_graph_image()
        report.build_graph()

        for y in self.adb_device_list:
            # Table 1
            report.set_obj_html("Real Client " + y.split(".")[2] + " Reset Observations",
                                "The below table shows actual behaviour of real devices for every reset value")
            report.build_objective()
            reset_count_ = list(reset_dict.keys())
            reset_count = []
            for i in reset_count_:
                reset_count.append(int(i) + 1)
            asso_attempts, conn_fail, asso_rej, asso_timeout, connected = [], [], [], [], []

            for i in reset_dict:
                asso_attempts.append(reset_dict[i][y]["ConnectAttempt"])
                conn_fail.append(reset_dict[i][y]["ConnectFailure"])
                asso_rej.append(reset_dict[i][y]["AssocRej"])
                asso_timeout.append(reset_dict[i][y]["AssocTimeout"])
                connected.append(reset_dict[i][y]["Connected"])
            table_1 = {
                "Reset Count": reset_count,
                "Association attempts": asso_attempts,
                "Connection Failure": conn_fail,
                "Association Rejection Count": asso_rej,
                "Association Timeout Count": asso_timeout,
                "Connected": connected
            }
            test_setup = pd.DataFrame(table_1)
            report.set_table_dataframe(test_setup)
            report.build_table()

        report.set_obj_html("Real Client Detail Info",
                            "The below table shows detail information of real clients")
        report.build_objective()
        d_name = self.get_device_details(query="name")
        # print(d_name)
        device = self.get_device_details(query="device")
        # print(device)
        model = self.get_device_details(query="model")
        # print(model)
        user_name = self.get_device_details(query="user-name")
        # print(user_name)
        release = self.get_device_details(query="release")
        # print(release)
        s_no = []
        for i in range(len(d_name)):
            s_no.append(i + 1)

        table_2 = {
            "S.No": s_no,
            "Name": d_name,
            "device": device,
            "user-name": user_name,
            "model": model,
            "release": release
        }
        test_setup = pd.DataFrame(table_2)
        report.set_table_dataframe(test_setup)
        report.build_table()

        test_input_infor = {
            "LANforge ip": self.host,
            "LANforge port": "8080",
            "ssid": self.ssid,
            "band": self.band,
            "reset count": self.reset,
            "time interval between every reset(sec)": self.time_int,
            "No of Clients": self.clients,
            "Contact": "support@candelatech.com"
        }
        report.set_table_title("Test basic Input Information")
        report.build_table_title()
        report.test_setup_table(value="Information", test_setup_data=test_input_infor)

        report.build_footer()
        report.write_html()
        report.write_pdf_with_timestamp(_page_size='A4', _orientation='Landscape')


def main():
    desc = """ port reset test 
    run: lf_interop_port_reset_test.py --host 192.168.1.31
    """
    parser = argparse.ArgumentParser(
        prog=__file__,
        formatter_class=argparse.RawTextHelpFormatter,
        description=desc)

    parser.add_argument("--host", "--mgr", default='192.168.1.31',
                        help='specify the GUI to connect to, assumes port 8080')

    parser.add_argument("--dut", default="TestDut",
                        help='specify DUT name on which the test will be running')

    parser.add_argument("--ssid", default="Airtel_9755718444_5GHz",
                        help='specify ssid on which the test will be running')

    parser.add_argument("--passwd", default="air29723",
                        help='specify encryption password  on which the test will be running')

    parser.add_argument("--encryp", default="psk2",
                        help='specify the encryption type  on which the test will be running eg :open|psk|psk2|sae|psk2jsae')

    parser.add_argument("--band", default="5G",
                        help='specify the type of band you want to perform testing eg 5G|2G|Dual')

    parser.add_argument("--clients", type=str, default="2",
                        help='specify the no of clients you want to perform test on')

    parser.add_argument("--reset", type=int, default=2,
                        help='specify the number of time you want to reset eg 2')

    parser.add_argument("--time_int", type=int, default=2,
                        help='specify the time interval in secs after which reset should happen')

    args = parser.parse_args()
    obj = InteropPortReset(host=args.host,
                           dut=args.dut,
                           ssid=args.ssid,
                           passwd=args.passwd,
                           encryp=args.encryp,
                           band=args.band,
                           clients=args.clients,
                           reset=args.reset,
                           time_int=args.time_int
                           )
    reset_dict, duration = obj.run()
    obj.generate_report(reset_dict=reset_dict, test_dur=duration)


if __name__ == '__main__':
    main()