
#!/usr/bin/env python3
from LANforge.lfcli_base import LFCliBase
from LANforge import LFRequest
from LANforge import LFUtils
from LANforge import set_port
import pprint
from pprint import pprint
import time





class MACVLANProfile(LFCliBase):
    def __init__(self, lfclient_host, lfclient_port,
                 local_realm,
                 macvlan_parent="eth1",
                 num_macvlans=1,
                 admin_down=False,
                 dhcp=False,
                 debug_=False):
        super().__init__(lfclient_host, lfclient_port, debug_)
        self.local_realm = local_realm
        self.num_macvlans = num_macvlans
        self.macvlan_parent = macvlan_parent
        self.resource = 1
        self.shelf = 1
        self.desired_macvlans = []
        self.created_macvlans = []
        self.dhcp = dhcp
        self.netmask = None
        self.first_ip_addr = None
        self.gateway = None
        self.ip_list = []
        self.COMMANDS = ["set_port"]
        self.desired_set_port_cmd_flags = []
        self.desired_set_port_current_flags = []  # do not default down, "if_down"
        self.desired_set_port_interest_flags = ["current_flags"]  # do not default down, "ifdown"
        self.set_port_data = {
            "shelf": 1,
            "resource": 1,
            "port": None,
            "current_flags": 0,
            "interest": 0,  # (0x2 + 0x4000 + 0x800000)  # current, dhcp, down,
        }

    def add_named_flags(self, desired_list, command_ref):
        if desired_list is None:
            raise ValueError("addNamedFlags wants a list of desired flag names")
        if len(desired_list) < 1:
            print("addNamedFlags: empty desired list")
            return 0
        if (command_ref is None) or (len(command_ref) < 1):
            raise ValueError("addNamedFlags wants a maps of flag values")

        result = 0
        for name in desired_list:
            if (name is None) or (name == ""):
                continue
            if name not in command_ref:
                if self.debug:
                    pprint(command_ref)
                raise ValueError("flag %s not in map" % name)
            result += command_ref[name]

        return result

    def set_command_param(self, command_name, param_name, param_value):
        # we have to check what the param name is
        if (command_name is None) or (command_name == ""):
            return
        if (param_name is None) or (param_name == ""):
            return
        if command_name not in self.COMMANDS:
            raise ValueError("Command name name [%s] not defined in %s" % (command_name, self.COMMANDS))
            # return
        if command_name == "set_port":
            self.set_port_data[param_name] = param_value

    def set_command_flag(self, command_name, param_name, value):
        # we have to check what the param name is
        if (command_name is None) or (command_name == ""):
            return
        if (param_name is None) or (param_name == ""):
            return
        if command_name not in self.COMMANDS:
            print("Command name name [%s] not defined in %s" % (command_name, self.COMMANDS))
            return

        elif command_name == "set_port":
            if (param_name not in set_port.set_port_current_flags) and (
                    param_name not in set_port.set_port_cmd_flags) and (
                    param_name not in set_port.set_port_interest_flags):
                print("Parameter name [%s] not defined in set_port.py" % param_name)
                if self.debug:
                    pprint(set_port.set_port_cmd_flags)
                    pprint(set_port.set_port_current_flags)
                    pprint(set_port.set_port_interest_flags)
                return
            if (param_name in set_port.set_port_cmd_flags):
                if (value == 1) and (param_name not in self.desired_set_port_cmd_flags):
                    self.desired_set_port_cmd_flags.append(param_name)
                elif value == 0:
                    self.desired_set_port_cmd_flags.remove(param_name)
            elif (param_name in set_port.set_port_current_flags):
                if (value == 1) and (param_name not in self.desired_set_port_current_flags):
                    self.desired_set_port_current_flags.append(param_name)
                elif value == 0:
                    self.desired_set_port_current_flags.remove(param_name)
            elif (param_name in set_port.set_port_interest_flags):
                if (value == 1) and (param_name not in self.desired_set_port_interest_flags):
                    self.desired_set_port_interest_flags.append(param_name)
                elif value == 0:
                    self.desired_set_port_interest_flags.remove(param_name)
            else:
                raise ValueError("Unknown param name: " + param_name)

    def create(self, admin_down=False, debug=False, sleep_time=1):
        print("Creating MACVLANs...")
        req_url = "/cli-json/add_mvlan"

        if not self.dhcp and self.first_ip_addr is not None and self.netmask is not None and self.gateway is not None:
            self.desired_set_port_interest_flags.append("ip_address")
            self.desired_set_port_interest_flags.append("ip_Mask")
            self.desired_set_port_interest_flags.append("ip_gateway")
            self.ip_list = LFUtils.gen_ip_series(ip_addr=self.first_ip_addr, netmask=self.netmask,
                                                 num_ips=self.num_macvlans)

        if self.dhcp:
            print("Using DHCP")
            self.desired_set_port_current_flags.append("use_dhcp")
            self.desired_set_port_interest_flags.append("dhcp")

        self.set_port_data["current_flags"] = self.add_named_flags(self.desired_set_port_current_flags,
                                                                   set_port.set_port_current_flags)
        self.set_port_data["interest"] = self.add_named_flags(self.desired_set_port_interest_flags,
                                                              set_port.set_port_interest_flags)
        set_port_r = LFRequest.LFRequest(self.lfclient_url + "/cli-json/set_port")

        for i in range(len(self.desired_macvlans)):
            data = {
                "shelf": self.shelf,
                "resource": self.resource,
                "mac": "xx:xx:xx:*:*:xx",
                "port": self.local_realm.name_to_eid(self.macvlan_parent)[2],
                "index": int(self.desired_macvlans[i][self.desired_macvlans[i].index('#') + 1:]),
                #"dhcp": self.dhcp,
                "flags": None
            }
            if admin_down:
                data["flags"] = 1
            else:
                data["flags"] = 0
            self.created_macvlans.append("%s.%s.%s#%d" % (self.shelf, self.resource,
                                                          self.macvlan_parent, int(
                self.desired_macvlans[i][self.desired_macvlans[i].index('#') + 1:])))
            self.local_realm.json_post(req_url, data)
            time.sleep(sleep_time)

        LFUtils.wait_until_ports_appear(base_url=self.lfclient_url, port_list=self.created_macvlans)
        print(self.created_macvlans)

        time.sleep(5)

        for i in range(len(self.created_macvlans)):
            eid = self.local_realm.name_to_eid(self.created_macvlans[i])
            name = eid[2]
            self.set_port_data["port"] = name  # for set_port calls.
            if not self.dhcp and self.first_ip_addr is not None and self.netmask is not None \
                    and self.gateway is not None:
                self.set_port_data["ip_addr"] = self.ip_list[i]
                self.set_port_data["netmask"] = self.netmask
                self.set_port_data["gateway"] = self.gateway
            set_port_r.addPostData(self.set_port_data)
            json_response = set_port_r.jsonPost(debug)
            time.sleep(sleep_time)

    def cleanup(self):
        print("Cleaning up MACVLANs...")
        print(self.created_macvlans)
        for port_eid in self.created_macvlans:
            self.local_realm.rm_port(port_eid, check_exists=True)
            time.sleep(.02)
        # And now see if they are gone
        LFUtils.wait_until_ports_disappear(base_url=self.lfclient_url, port_list=self.created_macvlans)

    def admin_up(self):
        for macvlan in self.created_macvlans:
            self.local_realm.admin_up(macvlan)

    def admin_down(self):
        for macvlan in self.created_macvlans:
            self.local_realm.admin_down(macvlan)
