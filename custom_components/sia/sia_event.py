"""Module for SIA Events."""

import re


class SIAEvent:
    """Class for SIA Events."""

    def __init__(self, line):
        # Example events: 98100078"*SIA-DCS"5994L0#acct[5AB718E008C616BF16F6468033A11326B0F7546CAB230910BCA10E4DEBA42283C436E4F8EFF50931070DDE36D5BB5F0C
        # Example events: 66100078"*SIA-DCS"6001L0#acct[6F7457178C6F0EAD99109E1DC5B75B26EDFBE1AA17361CD48E0B0E340081035F16AD2A25CD3D7F04105EC1EA65BF6341
        # Example events: 2E680078"*SIA-DCS"6002L0#acct[FDDCDFEC950EDC3F7C438B75CD57B9C91E1CA632806882769097C60292F86BD13D43D3BA7E2F529560DC7B51E6581E58
        # Example events: 2E680078"SIA-DCS"6002L0#acct[|Nri1/CL501]_14:12:04,09-25-2019
        # Example events: 5BFD0078"*SIA-DCS"6003L0#acct[03D1EA959BCC9E2DA91CACA7AFF472F1CB234708977C4E1E3B86A8ABD45AD9F95F0EFFFF817EE5349572972325BFC856
        # Example events: 5BFD0078"SIA-DCS"6003L0#acct[|Nri1/OP501]_14:12:04,09-25-2019

        regex = r"(.{4})0[A-F0-9]{3}(\"(SIA-DCS|\*SIA-DCS)\"([0-9]{4})(R[A-F0-9]{1,6})?(L[A-F0-9]{1,6})#([A-F0-9]{3,16})\[([A-F0-9]*)?(.*Nri(\d*)/([a-zA-z]{2})(.*)]_([0-9:,-]*))?)"
        matches = re.findall(regex, line)

        # check if there is at lease one match
        if not matches:
            raise ValueError("SIAEvent: Constructor: no matches found.")
        self.msg_crc, self.full_message, self.message_type, self.sequence, self.receiver, self.prefix, self.account, self.content, self.zone, self.code, self.message, self.timestamp = matches[
            0
        ]
        self.calc_crc = SIAEvent.crc_calc(self.full_message)
        if self.code:
            self._add_sia()

    def _add_sia(self):
        """Finds the sia codes based on self.code."""
        full = self.all_codes.get(self.code, None)
        if full:
            self.type = full.get("type")
            self.description = full.get("description")
            self.concerns = full.get("concerns")
        else:
            raise LookupError("Code not found: {}".format(self.code))

    def parse_decrypted(self, new_data):
        """When the content was decrypted, update the fields contained within."""
        regex = r".*Nri(\d*)/([a-zA-z]{2})(.*)]_([0-9:,-]*)"
        matches = re.findall(regex, new_data)
        if not matches:
            raise ValueError("SIAEvent: Parse Decrypted: no matches found.")
        self.zone, self.code, self.message, self.timestamp = matches[0]
        if self.code:
            self._add_sia()

    @staticmethod
    def crc_calc(msg):
        """Calculate the CRC of the events."""
        crc = 0
        for letter in msg:
            temp = letter
            for _ in range(0, 8):
                temp ^= crc & 1
                crc >>= 1
                if (temp & 1) != 0:
                    crc ^= 0xA001
                temp >>= 1
        return str.encode(("%x" % crc).upper().zfill(4))

    @property
    def valid_message(self):
        """Check the validity of the message by comparing the sent CRC with the calculated CRC."""
        return self.msg_crc == self.calc_crc

    @property
    def sia_string(self):
        """Create a string with the SIA codes and some other fields."""
        return "Code: {}, Type: {}, Description: {}, Concerns: {}".format(
            self.code, self.type, self.description, self.concerns
        )

    def __str__(self):
        return "CRC: {}, Calc CRC: {}, Full Message: {}, Message type: {}, Sequence: {}, Receiver: {}, Prefix: {}, Account: {}, Content: {}, Zone: {}, Code: {}, Message: {}, Timestamp: {}, Code: {}, Type: {}, Description: {}, Concerns: {}".format(
            self.msg_crc,
            self.calc_crc,
            self.full_message,
            self.message_type,
            self.sequence,
            self.receiver,
            self.prefix,
            self.account,
            self.content,
            self.zone,
            self.code,
            self.message,
            self.timestamp,
            self.code,
            self.type,
            self.description,
            self.concerns,
        )

    all_codes = {
        "AA": {
            "code": "AA",
            "type": "Alarm – Panel Substitution",
            "description": "An attempt to substitute an alternate alarm panel for a secure panel has been made",
            "concerns": "Condition number",
        },
        "AB": {
            "code": "AB",
            "type": "Abort",
            "description": "An event message was not sent due to User action",
            "concerns": "Zone or point",
        },
        "AN": {
            "code": "AN",
            "type": "Analog Restoral",
            "description": "An analog fire sensor has been restored to normal operation",
            "concerns": "Zone or point",
        },
        "AR": {
            "code": "AR",
            "type": "AC Restoral",
            "description": "AC power has been restored",
            "concerns": "Unused",
        },
        "AS": {
            "code": "AS",
            "type": "Analog Service",
            "description": "An analog fire sensor needs to be cleaned or calibrated",
            "concerns": "Zone or point",
        },
        "AT": {
            "code": "AT",
            "type": "AC Trouble",
            "description": "AC power has been failed",
            "concerns": "Unused",
        },
        "BA": {
            "code": "BA",
            "type": "Burglary Alarm",
            "description": "Burglary zone has been violated while armed",
            "concerns": "Zone or point",
        },
        "BB": {
            "code": "BB",
            "type": "Burglary Bypass",
            "description": "Burglary zone has been bypassed",
            "concerns": "Zone or point",
        },
        "BC": {
            "code": "BC",
            "type": "Burglary Cancel",
            "description": "Alarm has been cancelled by authorized user",
            "concerns": "User number",
        },
        "BD": {
            "code": "BD",
            "type": "Swinger Trouble",
            "description": "A non-fire zone has been violated after a Swinger Shutdown on the zone",
            "concerns": "Zone or point",
        },
        "BE": {
            "code": "BE",
            "type": "Swinger Trouble Restore",
            "description": "A non-fire zone restores to normal from a Swinger Trouble state",
            "concerns": "Zone or point",
        },
        "BG": {
            "code": "BG",
            "type": "Unverified Event - Burglary",
            "description": "A point assigned to a Cross Point group has gone into alarm but the Cross Point remained normal",
            "concerns": "Zone or point",
        },
        "BH": {
            "code": "BH",
            "type": "Burglary Alarm Restore",
            "description": "Alarm condition eliminated",
            "concerns": "Zone or point",
        },
        "BJ": {
            "code": "BJ",
            "type": "Burglary Trouble Restore",
            "description": "Trouble condition eliminated",
            "concerns": "Zone or point",
        },
        "BM": {
            "code": "BM",
            "type": "Burglary Alarm - Cross Point",
            "description": "Burglary alarm w/cross point also in alarm - alarm verified",
            "concerns": "Zone or point",
        },
        "BR": {
            "code": "BR",
            "type": "Burglary Restoral",
            "description": "Alarm/trouble condition has been eliminated",
            "concerns": "Zone or point",
        },
        "BS": {
            "code": "BS",
            "type": "Burglary Supervisory",
            "description": "Unsafe intrusion detection system condition",
            "concerns": "Zone or point",
        },
        "BT": {
            "code": "BT",
            "type": "Burglary Trouble",
            "description": "Burglary zone disabled by fault",
            "concerns": "Zone or point",
        },
        "BU": {
            "code": "BU",
            "type": "Burglary Unbypass",
            "description": "Zone bypass has been removed",
            "concerns": "Zone or point",
        },
        "BV": {
            "code": "BV",
            "type": "Burglary Verified",
            "description": "A burglary alarm has occurred and been verified within programmed conditions. (zone or point not sent)",
            "concerns": "Area number",
        },
        "BX": {
            "code": "BX",
            "type": "Burglary Test",
            "description": "Burglary zone activated during testing",
            "concerns": "Zone or point",
        },
        "BZ": {
            "code": "BZ",
            "type": "Missing Supervision",
            "description": "A non-fire Supervisory point has gone missing",
            "concerns": "Zone or point",
        },
        "CA": {
            "code": "CA",
            "type": "Automatic Closing",
            "description": "System armed automatically",
            "concerns": "Area number",
        },
        "CD": {
            "code": "CD",
            "type": "Closing Delinquent",
            "description": "The system has not been armed for a programmed amount of time",
            "concerns": "Area number",
        },
        "CE": {
            "code": "CE",
            "type": "Closing Extend",
            "description": "Extend closing time",
            "concerns": "User number",
        },
        "CF": {
            "code": "CF",
            "type": "Forced Closing",
            "description": "System armed, some zones not ready",
            "concerns": "User number",
        },
        "CG": {
            "code": "CG",
            "type": "Close Area",
            "description": "System has been partially armed",
            "concerns": "Area number",
        },
        "CI": {
            "code": "CI",
            "type": "Fail to Close",
            "description": "An area has not been armed at the end of the closing window",
            "concerns": "Area number",
        },
        "CJ": {
            "code": "CJ",
            "type": "Late Close",
            "description": "An area was armed after the closing window",
            "concerns": "User number",
        },
        "CK": {
            "code": "CK",
            "type": "Early Close",
            "description": "An area was armed before the closing window",
            "concerns": "User number",
        },
        "CL": {
            "code": "CL",
            "type": "Closing Report",
            "description": "System armed, normal",
            "concerns": "User number",
        },
        "CM": {
            "code": "CM",
            "type": "Missing Alarm - Recent Closing",
            "description": "A point has gone missing within 2 minutes of closing",
            "concerns": "Zone or point",
        },
        "CO": {
            "code": "CO",
            "type": "Command Sent",
            "description": "A command has been sent to an expansion/peripheral device",
            "concerns": "Condition number",
        },
        "CP": {
            "code": "CP",
            "type": "Automatic Closing",
            "description": "System armed automatically",
            "concerns": "User number",
        },
        "CQ": {
            "code": "CQ",
            "type": "Remote Closing",
            "description": "The system was armed from a remote location",
            "concerns": "User number",
        },
        "CR": {
            "code": "CR",
            "type": "Recent Closing",
            "description": "An alarm occurred within five minutes after the system was closed",
            "concerns": "User number",
        },
        "CS": {
            "code": "CS",
            "type": "Closing Keyswitch",
            "description": "Account has been armed by keyswitch",
            "concerns": "Zone or point",
        },
        "CT": {
            "code": "CT",
            "type": "Late to Open",
            "description": "System was not disarmed on time",
            "concerns": "Area number",
        },
        "CW": {
            "code": "CW",
            "type": "Was Force Armed",
            "description": "Header for a force armed session, forced point msgs may follow",
            "concerns": "Area number",
        },
        "CX": {
            "code": "CX",
            "type": "Custom Function Executed",
            "description": "The panel has executed a preprogrammed set of instructions",
            "concerns": "Custom Function number",
        },
        "CZ": {
            "code": "CZ",
            "type": "Point Closing",
            "description": "A point, as opposed to a whole area or account, has closed",
            "concerns": "Zone or point",
        },
        "DA": {
            "code": "DA",
            "type": "Card Assigned",
            "description": "An access ID has been added to the controller",
            "concerns": "User number",
        },
        "DB": {
            "code": "DB",
            "type": "Card Deleted",
            "description": "An access ID has been deleted from the controller",
            "concerns": "User number",
        },
        "DC": {
            "code": "DC",
            "type": "Access Closed",
            "description": "Access to all users prohibited",
            "concerns": "Door number",
        },
        "DD": {
            "code": "DD",
            "type": "Access Denied",
            "description": "Access denied, unknown code",
            "concerns": "Door number",
        },
        "DE": {
            "code": "DE",
            "type": "Request to Enter",
            "description": "An access point was opened via a Request to Enter device",
            "concerns": "Door number",
        },
        "DF": {
            "code": "DF",
            "type": "Door Forced",
            "description": "Door opened without access request",
            "concerns": "Door number",
        },
        "DG": {
            "code": "DG",
            "type": "Access Granted",
            "description": "Door access granted",
            "concerns": "Door number",
        },
        "DH": {
            "code": "DH",
            "type": "Door Left Open - Restoral",
            "description": "An access point in a Door Left Open state has restored",
            "concerns": "Door number",
        },
        "DI": {
            "code": "DI",
            "type": "Access Denied – Passback",
            "description": "Access denied because credential has not exited area before attempting to re-enter same area",
            "concerns": "Door number",
        },
        "DJ": {
            "code": "DJ",
            "type": "Door Forced - Trouble",
            "description": "An access point has been forced open in an unarmed area",
            "concerns": "Door number",
        },
        "DK": {
            "code": "DK",
            "type": "Access Lockout",
            "description": "Access denied, known code",
            "concerns": "Door number",
        },
        "DL": {
            "code": "DL",
            "type": "Door Left Open - Alarm",
            "description": "An open access point when open time expired in an armed area",
            "concerns": "Door number",
        },
        "DM": {
            "code": "DM",
            "type": "Door Left Open - Trouble",
            "description": "An open access point when open time expired in an unarmed area",
            "concerns": "Door number",
        },
        "DN": {
            "code": "DN",
            "type": "Door Left Open (non-alarm, non-trouble)",
            "description": "An access point was open when the door cycle time expired",
            "concerns": "Door number",
        },
        "DO": {
            "code": "DO",
            "type": "Access Open",
            "description": "Access to authorized users allowed",
            "concerns": "Door number",
        },
        "DP": {
            "code": "DP",
            "type": "Access Denied - Unauthorized Time",
            "description": "An access request was denied because the request is occurring outside the user’s authorized time window(s)",
            "concerns": "Door number",
        },
        "DQ": {
            "code": "DQ",
            "type": "Access Denied - Unauthorized Arming State",
            "description": "An access request was denied because the user was not authorized in this area when the area was armed",
            "concerns": "Door number",
        },
        "DR": {
            "code": "DR",
            "type": "Door Restoral",
            "description": "Access alarm/trouble condition eliminated",
            "concerns": "Door number",
        },
        "DS": {
            "code": "DS",
            "type": "Door Station",
            "description": "Identifies door for next report",
            "concerns": "Door number",
        },
        "DT": {
            "code": "DT",
            "type": "Access Trouble",
            "description": "Access system trouble",
            "concerns": "Unused",
        },
        "DU": {
            "code": "DU",
            "type": "Dealer ID",
            "description": "Dealer ID number",
            "concerns": "Dealer ID",
        },
        "DV": {
            "code": "DV",
            "type": "Access Denied - Unauthorized Entry Level",
            "description": "An access request was denied because the user is not authorized in this area",
            "concerns": "Door number",
        },
        "DW": {
            "code": "DW",
            "type": "Access Denied - Interlock",
            "description": "An access request was denied because the doors associated Interlock point is open",
            "concerns": "Door number",
        },
        "DX": {
            "code": "DX",
            "type": "Request to Exit",
            "description": "An access point was opened via a Request to Exit device",
            "concerns": "Door number",
        },
        "DY": {
            "code": "DY",
            "type": "Door Locked",
            "description": "The door’s lock has been engaged",
            "concerns": "Door number",
        },
        "DZ": {
            "code": "DZ",
            "type": "Access Denied - Door Secured",
            "description": "An access request was denied because the door has been placed in an Access Closed state",
            "concerns": "Door number",
        },
        "EA": {
            "code": "EA",
            "type": "Exit Alarm",
            "description": "An exit zone remained violated at the end of the exit delay period",
            "concerns": "Zone or point",
        },
        "EE": {
            "code": "EE",
            "type": "Exit Error",
            "description": "An exit zone remained violated at the end of the exit delay period",
            "concerns": "User number",
        },
        "EJ": {
            "code": "EJ",
            "type": "Expansion Tamper Restore",
            "description": "Expansion device tamper restoral",
            "concerns": "Expansion device number",
        },
        "EM": {
            "code": "EM",
            "type": "Expansion Device Missing",
            "description": "Expansion device missing",
            "concerns": "Expansion device number",
        },
        "EN": {
            "code": "EN",
            "type": "Expansion Missing Restore",
            "description": "Expansion device communications re-established",
            "concerns": "Expansion device number",
        },
        "ER": {
            "code": "ER",
            "type": "Expansion Restoral",
            "description": "Expansion device trouble eliminated",
            "concerns": "Expander number",
        },
        "ES": {
            "code": "ES",
            "type": "Expansion Device Tamper",
            "description": "Expansion device enclosure tamper",
            "concerns": "Expansion device number",
        },
        "ET": {
            "code": "ET",
            "type": "Expansion Trouble",
            "description": "Expansion device trouble",
            "concerns": "Expander number",
        },
        "EX": {
            "code": "EX",
            "type": "External Device Condition",
            "description": "A specific reportable condition is detected on an external device",
            "concerns": "Device number",
        },
        "EZ": {
            "code": "EZ",
            "type": "Missing Alarm - Exit Error",
            "description": "A point remained missing at the end of the exit delay period",
            "concerns": "Point number",
        },
        "FA": {
            "code": "FA",
            "type": "Fire Alarm",
            "description": "Fire condition detected",
            "concerns": "Zone or point",
        },
        "FB": {
            "code": "FB",
            "type": "Fire Bypass",
            "description": "Zone has been bypassed",
            "concerns": "Zone or point",
        },
        "FC": {
            "code": "FC",
            "type": "Fire Cancel",
            "description": "A Fire Alarm has been cancelled by an authorized person",
            "concerns": "Zone or point",
        },
        "FG": {
            "code": "FG",
            "type": "Unverified Event – Fire",
            "description": "A point assigned to a Cross Point group has gone into alarm but the Cross Point remained normal",
            "concerns": "Zone or point",
        },
        "FH": {
            "code": "FH",
            "type": "Fire Alarm Restore",
            "description": "Alarm condition eliminated",
            "concerns": "Zone or point",
        },
        "FI": {
            "code": "FI",
            "type": "Fire Test Begin",
            "description": "The transmitter area's fire test has begun",
            "concerns": "Area number",
        },
        "FJ": {
            "code": "FJ",
            "type": "Fire Trouble Restore",
            "description": "Trouble condition eliminated",
            "concerns": "Zone or point",
        },
        "FK": {
            "code": "FK",
            "type": "Fire Test End",
            "description": "The transmitter area's fire test has ended",
            "concerns": "Area number",
        },
        "FL": {
            "code": "FL",
            "type": "Fire Alarm Silenced",
            "description": "The fire panel’s sounder was silenced by command",
            "concerns": "Zone or point",
        },
        "FM": {
            "code": "FM",
            "type": "Fire Alarm - Cross Point",
            "description": "Fire Alarm with Cross Point also in alarm verifying the Fire Alarm",
            "concerns": "Point number",
        },
        "FQ": {
            "code": "FQ",
            "type": "Fire Supervisory Trouble Restore",
            "description": "A fire supervisory zone that was in trouble condition has now restored to normal",
            "concerns": "Zone or point",
        },
        "FR": {
            "code": "FR",
            "type": "Fire Restoral",
            "description": "Alarm/trouble condition has been eliminated",
            "concerns": "Zone or point",
        },
        "FS": {
            "code": "FS",
            "type": "Fire Supervisory",
            "description": "Unsafe fire detection system condition",
            "concerns": "Zone or point",
        },
        "FT": {
            "code": "FT",
            "type": "Fire Trouble",
            "description": "Zone disabled by fault",
            "concerns": "Zone or point",
        },
        "FU": {
            "code": "FU",
            "type": "Fire Unbypass",
            "description": "Bypass has been removed",
            "concerns": "Zone or point",
        },
        "FV": {
            "code": "FV",
            "type": "Fire Supervision Restore",
            "description": "A fire supervision zone that was in alarm has restored to normal",
            "concerns": "Zone or point",
        },
        "FW": {
            "code": "FW",
            "type": "Fire Supervisory Trouble",
            "description": "A fire supervisory zone is now in a trouble condition",
            "concerns": "Zone or point",
        },
        "FX": {
            "code": "FX",
            "type": "Fire Test",
            "description": "Fire zone activated during test",
            "concerns": "Zone or point",
        },
        "FY": {
            "code": "FY",
            "type": "Missing Fire Trouble",
            "description": "A fire point is now logically missing",
            "concerns": "Zone or point",
        },
        "FZ": {
            "code": "FZ",
            "type": "Missing Fire Supervision",
            "description": "A Fire Supervisory point has gone missing",
            "concerns": "Zone or point",
        },
        "GA": {
            "code": "GA",
            "type": "Gas Alarm",
            "description": "Gas alarm condition detected",
            "concerns": "Zone or point",
        },
        "GB": {
            "code": "GB",
            "type": "Gas Bypass",
            "description": "Zone has been bypassed",
            "concerns": "Zone or point",
        },
        "GH": {
            "code": "GH",
            "type": "Gas Alarm Restore",
            "description": "Alarm condition eliminated",
            "concerns": "Zone or point",
        },
        "GJ": {
            "code": "GJ",
            "type": "Gas Trouble Restore",
            "description": "Trouble condition eliminated",
            "concerns": "Zone or point",
        },
        "GR": {
            "code": "GR",
            "type": "Gas Restoral",
            "description": "Alarm/trouble condition has been eliminated",
            "concerns": "Zone or point",
        },
        "GS": {
            "code": "GS",
            "type": "Gas Supervisory",
            "description": "Unsafe gas detection system condition",
            "concerns": "Zone or point",
        },
        "GT": {
            "code": "GT",
            "type": "Gas Trouble",
            "description": "Zone disabled by fault",
            "concerns": "Zone or point",
        },
        "GU": {
            "code": "GU",
            "type": "Gas Unbypass",
            "description": "Bypass has been removed",
            "concerns": "Zone or point",
        },
        "GX": {
            "code": "GX",
            "type": "Gas Test",
            "description": "Zone activated during test",
            "concerns": "Zone or point",
        },
        "HA": {
            "code": "HA",
            "type": "Holdup Alarm",
            "description": "Silent alarm, user under duress",
            "concerns": "Zone or point",
        },
        "HB": {
            "code": "HB",
            "type": "Holdup Bypass",
            "description": "Zone has been bypassed",
            "concerns": "Zone or point",
        },
        "HH": {
            "code": "HH",
            "type": "Holdup Alarm Restore",
            "description": "Alarm condition eliminated",
            "concerns": "Zone or point",
        },
        "HJ": {
            "code": "HJ",
            "type": "Holdup Trouble Restore",
            "description": "Trouble condition eliminated",
            "concerns": "Zone or point",
        },
        "HR": {
            "code": "HR",
            "type": "Holdup Restoral",
            "description": "Alarm/trouble condition has been eliminated",
            "concerns": "Zone or point",
        },
        "HS": {
            "code": "HS",
            "type": "Holdup Supervisory",
            "description": "Unsafe holdup system condition",
            "concerns": "Zone or point",
        },
        "HT": {
            "code": "HT",
            "type": "Holdup Trouble",
            "description": "Zone disabled by fault",
            "concerns": "Zone or point",
        },
        "HU": {
            "code": "HU",
            "type": "Holdup Unbypass",
            "description": "Bypass has been removed",
            "concerns": "Zone or point",
        },
        "IA": {
            "code": "IA",
            "type": "Equipment Failure Condition",
            "description": "A specific, reportable condition is detected on a device",
            "concerns": "Point number",
        },
        "IR": {
            "code": "IR",
            "type": "Equipment Fail - Restoral",
            "description": "The equipment condition has been restored to normal",
            "concerns": "Point number",
        },
        "JA": {
            "code": "JA",
            "type": "User code Tamper",
            "description": "Too many unsuccessful attempts have been made to enter a user ID",
            "concerns": "Area number",
        },
        "JD": {
            "code": "JD",
            "type": "Date Changed",
            "description": "The date was changed in the transmitter/receiver",
            "concerns": "User number",
        },
        "JH": {
            "code": "JH",
            "type": "Holiday Changed",
            "description": "The transmitter's holiday schedule has been changed",
            "concerns": "User number",
        },
        "JK": {
            "code": "JK",
            "type": "Latchkey Alert",
            "description": "A designated user passcode has not been entered during a scheduled time window",
            "concerns": "User number",
        },
        "JL": {
            "code": "JL",
            "type": "Log Threshold",
            "description": "The transmitter's log memory has reached its threshold level",
            "concerns": "Unused",
        },
        "JO": {
            "code": "JO",
            "type": "Log Overflow",
            "description": "The transmitter's log memory has overflowed",
            "concerns": "Unused",
        },
        "JP": {
            "code": "JP",
            "type": "User On Premises",
            "description": "A designated user passcode has been used to gain access to the premises.",
            "concerns": "User number",
        },
        "JR": {
            "code": "JR",
            "type": "Schedule Executed",
            "description": "An automatic scheduled event was executed",
            "concerns": "Area number",
        },
        "JS": {
            "code": "JS",
            "type": "Schedule Changed",
            "description": "An automatic schedule was changed",
            "concerns": "User number",
        },
        "JT": {
            "code": "JT",
            "type": "Time Changed",
            "description": "The time was changed in the transmitter/receiver",
            "concerns": "User number",
        },
        "JV": {
            "code": "JV",
            "type": "User code Changed",
            "description": "A user's code has been changed",
            "concerns": "User number",
        },
        "JX": {
            "code": "JX",
            "type": "User code Deleted",
            "description": "A user's code has been removed",
            "concerns": "User number",
        },
        "JY": {
            "code": "JY",
            "type": "User code Added",
            "description": "A user’s code has been added",
            "concerns": "User number",
        },
        "JZ": {
            "code": "JZ",
            "type": "User Level Set",
            "description": "A user’s authority level has been set",
            "concerns": "User number",
        },
        "KA": {
            "code": "KA",
            "type": "Heat Alarm",
            "description": "High temperature detected on premise",
            "concerns": "Zone or point",
        },
        "KB": {
            "code": "KB",
            "type": "Heat Bypass",
            "description": "Zone has been bypassed",
            "concerns": "Zone or point",
        },
        "KH": {
            "code": "KH",
            "type": "Heat Alarm Restore",
            "description": "Alarm condition eliminated",
            "concerns": "Zone or point",
        },
        "KJ": {
            "code": "KJ",
            "type": "Heat Trouble Restore",
            "description": "Trouble condition eliminated",
            "concerns": "Zone or point",
        },
        "KR": {
            "code": "KR",
            "type": "Heat Restoral",
            "description": "Alarm/trouble condition has been eliminated",
            "concerns": "Zone or point",
        },
        "KS": {
            "code": "KS",
            "type": "Heat Supervisory",
            "description": "Unsafe heat detection system condition",
            "concerns": "Zone or point",
        },
        "KT": {
            "code": "KT",
            "type": "Heat Trouble",
            "description": "Zone disabled by fault",
            "concerns": "Zone or point",
        },
        "KU": {
            "code": "KU",
            "type": "Heat Unbypass",
            "description": "Bypass has been removed",
            "concerns": "Zone or point",
        },
        "LB": {
            "code": "LB",
            "type": "Local Program",
            "description": "Begin local programming",
            "concerns": "Unused",
        },
        "LD": {
            "code": "LD",
            "type": "Local Program Denied",
            "description": "Access code incorrect",
            "concerns": "Unused",
        },
        "LE": {
            "code": "LE",
            "type": "Listen-in Ended",
            "description": "The listen-in session has been terminated",
            "concerns": "Unused",
        },
        "LF": {
            "code": "LF",
            "type": "Listen-in Begin",
            "description": "The listen-in session with the RECEIVER has begun",
            "concerns": "Unused",
        },
        "LR": {
            "code": "LR",
            "type": "Phone Line Restoral",
            "description": "Phone line restored to service",
            "concerns": "Line number",
        },
        "LS": {
            "code": "LS",
            "type": "Local Program Success",
            "description": "Local programming successful",
            "concerns": "Unused",
        },
        "LT": {
            "code": "LT",
            "type": "Phone Line Trouble",
            "description": "Phone line trouble report",
            "concerns": "Line number",
        },
        "LU": {
            "code": "LU",
            "type": "Local Program Fail",
            "description": "Local programming unsuccessful",
            "concerns": "Unused",
        },
        "LX": {
            "code": "LX",
            "type": "Local Programming Ended",
            "description": "A local programming session has been terminated",
            "concerns": "Unused",
        },
        "MA": {
            "code": "MA",
            "type": "Medical Alarm",
            "description": "Emergency assistance request",
            "concerns": "Zone or point",
        },
        "MB": {
            "code": "MB",
            "type": "Medical Bypass",
            "description": "Zone has been bypassed",
            "concerns": "Zone or point",
        },
        "MH": {
            "code": "MH",
            "type": "Medical Alarm Restore",
            "description": "Alarm condition eliminated",
            "concerns": "Zone or point",
        },
        "MI": {
            "code": "MI",
            "type": "Message",
            "description": "A canned message is being sent",
            "concerns": "Message number",
        },
        "MJ": {
            "code": "MJ",
            "type": "Medical Trouble Restore",
            "description": "Trouble condition eliminated",
            "concerns": "Zone or point",
        },
        "MR": {
            "code": "MR",
            "type": "Medical Restoral",
            "description": "Alarm/trouble condition has been eliminated",
            "concerns": "Zone or point",
        },
        "MS": {
            "code": "MS",
            "type": "Medical Supervisory",
            "description": "Unsafe system condition exists",
            "concerns": "Zone or point",
        },
        "MT": {
            "code": "MT",
            "type": "Medical Trouble",
            "description": "Zone disabled by fault",
            "concerns": "Zone or point",
        },
        "MU": {
            "code": "MU",
            "type": "Medical Unbypass",
            "description": "Bypass has been removed",
            "concerns": "Zone or point",
        },
        "NA": {
            "code": "NA",
            "type": "No Activity",
            "description": "There has been no zone activity for a programmed amount of time",
            "concerns": "Zone number",
        },
        "NC": {
            "code": "NC",
            "type": "Network Condition",
            "description": "A communications network has a specific reportable condition",
            "concerns": "Network number",
        },
        "NF": {
            "code": "NF",
            "type": "Forced Perimeter Arm",
            "description": "Some zones/points not ready",
            "concerns": "Area number",
        },
        "NL": {
            "code": "NL",
            "type": "Perimeter Armed",
            "description": "An area has been perimeter armed",
            "concerns": "Area number",
        },
        "NM": {
            "code": "NM",
            "type": "Perimeter Armed, User Defined",
            "description": "A user defined area has been perimeter armed",
            "concerns": "Area number",
        },
        "NR": {
            "code": "NR",
            "type": "Network Restoral",
            "description": "A communications network has returned to normal operation",
            "concerns": "Network number",
        },
        "NS": {
            "code": "NS",
            "type": "Activity Resumed",
            "description": "A zone has detected activity after an alert",
            "concerns": "Zone number",
        },
        "NT": {
            "code": "NT",
            "type": "Network Failure",
            "description": "A communications network has failed",
            "concerns": "Network number",
        },
        "OA": {
            "code": "OA",
            "type": "Automatic Opening",
            "description": "System has disarmed automatically",
            "concerns": "Area number",
        },
        "OC": {
            "code": "OC",
            "type": "Cancel Report",
            "description": "Untyped zone cancel",
            "concerns": "User number",
        },
        "OG": {
            "code": "OG",
            "type": "Open Area",
            "description": "System has been partially disarmed",
            "concerns": "Area number",
        },
        "OH": {
            "code": "OH",
            "type": "Early to Open from Alarm",
            "description": "An area in alarm was disarmed before the opening window",
            "concerns": "User number",
        },
        "OI": {
            "code": "OI",
            "type": "Fail to Open",
            "description": "An area has not been armed at the end of the opening window",
            "concerns": "Area number",
        },
        "OJ": {
            "code": "OJ",
            "type": "Late Open",
            "description": "An area was disarmed after the opening window",
            "concerns": "User number",
        },
        "OK": {
            "code": "OK",
            "type": "Early Open",
            "description": "An area was disarmed before the opening window",
            "concerns": "User number",
        },
        "OL": {
            "code": "OL",
            "type": "Late to Open from Alarm",
            "description": "An area in alarm was disarmed after the opening window",
            "concerns": "User number",
        },
        "OP": {
            "code": "OP",
            "type": "Opening Report",
            "description": "Account was disarmed",
            "concerns": "User number",
        },
        "OQ": {
            "code": "OQ",
            "type": "Remote Opening",
            "description": "The system was disarmed from a remote location",
            "concerns": "User number",
        },
        "OR": {
            "code": "OR",
            "type": "Disarm From Alarm",
            "description": "Account in alarm was reset/disarmed",
            "concerns": "User number",
        },
        "OS": {
            "code": "OS",
            "type": "Opening Keyswitch",
            "description": "Account has been disarmed by keyswitch",
            "concerns": "Zone or point",
        },
        "OT": {
            "code": "OT",
            "type": "Late To Close",
            "description": "System was not armed on time",
            "concerns": "User number",
        },
        "OU": {
            "code": "OU",
            "type": "Output State – Trouble",
            "description": "An output on a peripheral device or NAC is not functioning",
            "concerns": "Output number",
        },
        "OV": {
            "code": "OV",
            "type": "Output State – Restore",
            "description": "An output on a peripheral device or NAC is back to normal operation",
            "concerns": "Output number",
        },
        "OZ": {
            "code": "OZ",
            "type": "Point Opening",
            "description": "A point, rather than a full area or account, disarmed",
            "concerns": "Zone or point",
        },
        "PA": {
            "code": "PA",
            "type": "Panic Alarm",
            "description": "Emergency assistance request, manually activated",
            "concerns": "Zone or point",
        },
        "PB": {
            "code": "PB",
            "type": "Panic Bypass",
            "description": "Panic zone has been bypassed",
            "concerns": "Zone or point",
        },
        "PH": {
            "code": "PH",
            "type": "Panic Alarm Restore",
            "description": "Alarm condition eliminated",
            "concerns": "Zone or point",
        },
        "PJ": {
            "code": "PJ",
            "type": "Panic Trouble Restore",
            "description": "Trouble condition eliminated",
            "concerns": "Zone or point",
        },
        "PR": {
            "code": "PR",
            "type": "Panic Restoral",
            "description": "Alarm/trouble condition has been eliminated",
            "concerns": "Zone or point",
        },
        "PS": {
            "code": "PS",
            "type": "Panic Supervisory",
            "description": "Unsafe system condition exists",
            "concerns": "Zone or point",
        },
        "PT": {
            "code": "PT",
            "type": "Panic Trouble",
            "description": "Zone disabled by fault",
            "concerns": "Zone or point",
        },
        "PU": {
            "code": "PU",
            "type": "Panic Unbypass",
            "description": "Panic zone bypass has been removed",
            "concerns": "Zone or point",
        },
        "QA": {
            "code": "QA",
            "type": "Emergency Alarm",
            "description": "Emergency assistance request",
            "concerns": "Zone or point",
        },
        "QB": {
            "code": "QB",
            "type": "Emergency Bypass",
            "description": "Zone has been bypassed",
            "concerns": "Zone or point",
        },
        "QH": {
            "code": "QH",
            "type": "Emergency Alarm Restore",
            "description": "Alarm condition has been eliminated",
            "concerns": "Zone or point",
        },
        "QJ": {
            "code": "QJ",
            "type": "Emergency Trouble Restore",
            "description": "Trouble condition has been eliminated",
            "concerns": "Zone or point",
        },
        "QR": {
            "code": "QR",
            "type": "Emergency Restoral",
            "description": "Alarm/trouble condition has been eliminated",
            "concerns": "Zone or point",
        },
        "QS": {
            "code": "QS",
            "type": "Emergency Supervisory",
            "description": "Unsafe system condition exists",
            "concerns": "Zone or point",
        },
        "QT": {
            "code": "QT",
            "type": "Emergency Trouble",
            "description": "Zone disabled by fault",
            "concerns": "Zone or point",
        },
        "QU": {
            "code": "QU",
            "type": "Emergency Unbypass",
            "description": "Bypass has been removed",
            "concerns": "Zone or point",
        },
        "RA": {
            "code": "RA",
            "type": "Remote Programmer Call Failed",
            "description": "Transmitter failed to communicate with the remote programmer",
            "concerns": "Unused",
        },
        "RB": {
            "code": "RB",
            "type": "Remote Program Begin",
            "description": "Remote programming session initiated",
            "concerns": "Unused",
        },
        "RC": {
            "code": "RC",
            "type": "Relay Close",
            "description": "A relay has energized",
            "concerns": "Relay number",
        },
        "RD": {
            "code": "RD",
            "type": "Remote Program Denied",
            "description": "Access passcode incorrect",
            "concerns": "Unused",
        },
        "RN": {
            "code": "RN",
            "type": "Remote Reset",
            "description": "A TRANSMITTER was reset via a remote programmer",
            "concerns": "Unused",
        },
        "RO": {
            "code": "RO",
            "type": "Relay Open",
            "description": "A relay has de-energized",
            "concerns": "Relay number",
        },
        "RP": {
            "code": "RP",
            "type": "Automatic Test",
            "description": "Automatic communication test report",
            "concerns": "Unused",
        },
        "RR": {
            "code": "RR",
            "type": "Power Up",
            "description": "System lost power, is now restored",
            "concerns": "Unused",
        },
        "RS": {
            "code": "RS",
            "type": "Remote Program Success",
            "description": "Remote programming successful",
            "concerns": "Unused",
        },
        "RT": {
            "code": "RT",
            "type": "Data Lost",
            "description": "Dialer data lost, transmission error",
            "concerns": "Line number",
        },
        "RU": {
            "code": "RU",
            "type": "Remote Program Fail",
            "description": "Remote programming unsuccessful",
            "concerns": "Unused",
        },
        "RX": {
            "code": "RX",
            "type": "Manual Test",
            "description": "Manual communication test report",
            "concerns": "User number",
        },
        "RY": {
            "code": "RY",
            "type": "Test Off Normal",
            "description": "Test signal(s) indicates abnormal condition(s) exist",
            "concerns": "Zone or point",
        },
        "SA": {
            "code": "SA",
            "type": "Sprinkler Alarm",
            "description": "Sprinkler flow condition exists",
            "concerns": "Zone or point",
        },
        "SB": {
            "code": "SB",
            "type": "Sprinkler Bypass",
            "description": "Sprinkler zone has been bypassed",
            "concerns": "Zone or point",
        },
        "SC": {
            "code": "SC",
            "type": "Change of State",
            "description": "An expansion/peripheral device is reporting a new condition or state change",
            "concerns": "Condition number",
        },
        "SH": {
            "code": "SH",
            "type": "Sprinkler Alarm Restore",
            "description": "Alarm condition eliminated",
            "concerns": "Zone or point",
        },
        "SJ": {
            "code": "SJ",
            "type": "Sprinkler Trouble Restore",
            "description": "Trouble condition eliminated",
            "concerns": "Zone or point",
        },
        "SR": {
            "code": "SR",
            "type": "Sprinkler Restoral",
            "description": "Alarm/trouble condition has been eliminated",
            "concerns": "Zone or point",
        },
        "SS": {
            "code": "SS",
            "type": "Sprinkler Supervisory",
            "description": "Unsafe sprinkler system condition",
            "concerns": "Zone or point",
        },
        "ST": {
            "code": "ST",
            "type": "Sprinkler Trouble",
            "description": "Zone disabled by fault",
            "concerns": "Zone or point",
        },
        "SU": {
            "code": "SU",
            "type": "Sprinkler Unbypass",
            "description": "Sprinkler zone bypass has been removed",
            "concerns": "Zone or point",
        },
        "TA": {
            "code": "TA",
            "type": "Tamper Alarm",
            "description": "Alarm equipment enclosure opened",
            "concerns": "Zone or point",
        },
        "TB": {
            "code": "TB",
            "type": "Tamper Bypass",
            "description": "Tamper detection has been bypassed",
            "concerns": "Zone or point",
        },
        "TC": {
            "code": "TC",
            "type": "All Points Tested",
            "description": "All point tested",
            "concerns": "Unused",
        },
        "TE": {
            "code": "TE",
            "type": "Test End",
            "description": "Communicator restored to operation",
            "concerns": "Unused",
        },
        "TH": {
            "code": "TH",
            "type": "Tamper Alarm Restore",
            "description": "An Expansion Device’s tamper switch restores to normal from an Alarm state",
            "concerns": "Unused",
        },
        "TJ": {
            "code": "TJ",
            "type": "Tamper Trouble Restore",
            "description": "An Expansion Device’s tamper switch restores to normal from a Trouble state",
            "concerns": "Unused",
        },
        "TP": {
            "code": "TP",
            "type": "Walk Test Point",
            "description": "This point was tested during a Walk Test",
            "concerns": "Point number",
        },
        "TR": {
            "code": "TR",
            "type": "Tamper Restoral",
            "description": "Alarm equipment enclosure has been closed",
            "concerns": "Zone or point",
        },
        "TS": {
            "code": "TS",
            "type": "Test Start",
            "description": "Communicator taken out of operation",
            "concerns": "Unused",
        },
        "TT": {
            "code": "TT",
            "type": "Tamper Trouble",
            "description": "Equipment enclosure opened in disarmed state",
            "concerns": "Zone or point",
        },
        "TU": {
            "code": "TU",
            "type": "Tamper Unbypass",
            "description": "Tamper detection bypass has been removed",
            "concerns": "Zone or point",
        },
        "TW": {
            "code": "TW",
            "type": "Area Watch Start",
            "description": "Area watch feature has been activated",
            "concerns": "Unused",
        },
        "TX": {
            "code": "TX",
            "type": "Test Report",
            "description": "An unspecified (manual or automatic) communicator test",
            "concerns": "Unused",
        },
        "TZ": {
            "code": "TZ",
            "type": "Area Watch End",
            "description": "Area watch feature has been deactivated",
            "concerns": "Unused",
        },
        "UA": {
            "code": "UA",
            "type": "Untyped Zone Alarm",
            "description": "Alarm condition from zone of unknown type",
            "concerns": "Zone or point",
        },
        "UB": {
            "code": "UB",
            "type": "Untyped Zone Bypass",
            "description": "Zone of unknown type has been bypassed",
            "concerns": "Zone or point",
        },
        "UG": {
            "code": "UG",
            "type": "Unverified Event – Untyped",
            "description": "A point assigned to a Cross Point group has gone into alarm but the Cross Point remained normal",
            "concerns": "Zone or point",
        },
        "UH": {
            "code": "UH",
            "type": "Untyped Alarm Restore",
            "description": "Alarm condition eliminated",
            "concerns": "Zone or point",
        },
        "UJ": {
            "code": "UJ",
            "type": "Untyped Trouble Restore",
            "description": "Trouble condition eliminated",
            "concerns": "Zone or point",
        },
        "UR": {
            "code": "UR",
            "type": "Untyped Zone Restoral",
            "description": "Alarm/trouble condition eliminated from zone of unknown type",
            "concerns": "Zone or point",
        },
        "US": {
            "code": "US",
            "type": "Untyped Zone Supervisory",
            "description": "Unsafe condition from zone of unknown type",
            "concerns": "Zone or point",
        },
        "UT": {
            "code": "UT",
            "type": "Untyped Zone Trouble",
            "description": "Trouble condition from zone of unknown type",
            "concerns": "Zone or point",
        },
        "UU": {
            "code": "UU",
            "type": "Untyped Zone Unbypass",
            "description": "Bypass on zone of unknown type has been removed",
            "concerns": "Zone or point",
        },
        "UX": {
            "code": "UX",
            "type": "Undefined",
            "description": "An undefined alarm condition has occurred",
            "concerns": "Unused",
        },
        "UY": {
            "code": "UY",
            "type": "Untyped Missing Trouble",
            "description": "A point or device which was not armed is now logically missing",
            "concerns": "Zone or point",
        },
        "UZ": {
            "code": "UZ",
            "type": "Untyped Missing Alarm",
            "description": "A point or device which was armed is now logically missing",
            "concerns": "Zone or point",
        },
        "VI": {
            "code": "VI",
            "type": "Printer Paper In",
            "description": "TRANSMITTER or RECEIVER paper in",
            "concerns": "Printer number",
        },
        "VO": {
            "code": "VO",
            "type": "Printer Paper Out",
            "description": "TRANSMITTER or RECEIVER paper out",
            "concerns": "Printer number",
        },
        "VR": {
            "code": "VR",
            "type": "Printer Restore",
            "description": "TRANSMITTER or RECEIVER trouble restored",
            "concerns": "Printer number",
        },
        "VT": {
            "code": "VT",
            "type": "Printer Trouble",
            "description": "TRANSMITTER or RECEIVER trouble",
            "concerns": "Printer number",
        },
        "VX": {
            "code": "VX",
            "type": "Printer Test",
            "description": "TRANSMITTER or RECEIVER test",
            "concerns": "Printer number",
        },
        "VY": {
            "code": "VY",
            "type": "Printer Online",
            "description": "RECEIVER’S printer is now online",
            "concerns": "Unused",
        },
        "VZ": {
            "code": "VZ",
            "type": "Printer Offline",
            "description": "RECEIVER’S printer is now offline",
            "concerns": "Unused",
        },
        "WA": {
            "code": "WA",
            "type": "Water Alarm",
            "description": "Water detected at protected premises",
            "concerns": "Zone or point",
        },
        "WB": {
            "code": "WB",
            "type": "Water Bypass",
            "description": "Water detection has been bypassed",
            "concerns": "Zone or point",
        },
        "WH": {
            "code": "WH",
            "type": "Water Alarm Restore",
            "description": "Water alarm condition eliminated",
            "concerns": "Zone or point",
        },
        "WJ": {
            "code": "WJ",
            "type": "Water Trouble Restore",
            "description": "Water trouble condition eliminated",
            "concerns": "Zone or point",
        },
        "WR": {
            "code": "WR",
            "type": "Water Restoral",
            "description": "Water alarm/trouble condition has been eliminated",
            "concerns": "Zone or point",
        },
        "WS": {
            "code": "WS",
            "type": "Water Supervisory",
            "description": "Water unsafe water detection system condition",
            "concerns": "Zone or point",
        },
        "WT": {
            "code": "WT",
            "type": "Water Trouble",
            "description": "Water zone disabled by fault",
            "concerns": "Zone or point",
        },
        "WU": {
            "code": "WU",
            "type": "Water Unbypass",
            "description": "Water detection bypass has been removed",
            "concerns": "Zone or point",
        },
        "XA": {
            "code": "XA",
            "type": "Extra Account Report",
            "description": "CS RECEIVER has received an event from a non-existent account",
            "concerns": "Unused",
        },
        "XE": {
            "code": "XE",
            "type": "Extra Point",
            "description": "Panel has sensed an extra point not specified for this site",
            "concerns": "Point number",
        },
        "XF": {
            "code": "XF",
            "type": "Extra RF Point",
            "description": "Panel has sensed an extra RF point not specified for this site",
            "concerns": "Point number",
        },
        "XH": {
            "code": "XH",
            "type": "RF Interference Restoral",
            "description": "A radio device is no longer detecting RF Interference",
            "concerns": "Receiver number",
        },
        "XI": {
            "code": "XI",
            "type": "Sensor Reset",
            "description": "A user has reset a sensor",
            "concerns": "Zone or point",
        },
        "XJ": {
            "code": "XJ",
            "type": "RF Receiver Tamper Restoral",
            "description": "A Tamper condition at a premises RF Receiver has been restored",
            "concerns": "Receiver number",
        },
        "XL": {
            "code": "XL",
            "type": "Low Received Signal Strength",
            "description": "The RF signal strength of a reported event is below minimum level",
            "concerns": "Receiver number",
        },
        "XM": {
            "code": "XM",
            "type": "Missing Alarm - Cross Point",
            "description": "Missing Alarm verified by Cross Point in Alarm (or missing)",
            "concerns": "Zone or point",
        },
        "XQ": {
            "code": "XQ",
            "type": "RF Interference",
            "description": "A radio device is detecting RF Interference",
            "concerns": "Receiver number",
        },
        "XR": {
            "code": "XR",
            "type": "Transmitter Battery Restoral",
            "description": "Low battery has been corrected",
            "concerns": "Zone or point",
        },
        "XS": {
            "code": "XS",
            "type": "RF Receiver Tamper",
            "description": "A Tamper condition at a premises receiver is detected",
            "concerns": "Receiver number",
        },
        "XT": {
            "code": "XT",
            "type": "Transmitter Battery Trouble",
            "description": "Low battery in wireless transmitter",
            "concerns": "Zone or point",
        },
        "XW": {
            "code": "XW",
            "type": "Forced Point",
            "description": "A point was forced out of the system at arm time",
            "concerns": "Zone or point",
        },
        "XX": {
            "code": "XX",
            "type": "Fail to Test",
            "description": "A specific test from a panel was not received",
            "concerns": "Unused",
        },
        "YA": {
            "code": "YA",
            "type": "Bell Fault",
            "description": "A trouble condition has been detected on a Local Bell, Siren, or Annunciator",
            "concerns": "Unused",
        },
        "YB": {
            "code": "YB",
            "type": "Busy Seconds",
            "description": "Percent of time receiver's line card is on-line",
            "concerns": "Line card number",
        },
        "YC": {
            "code": "YC",
            "type": "Communications Fail",
            "description": "RECEIVER and TRANSMITTER",
            "concerns": "Unused",
        },
        "YD": {
            "code": "YD",
            "type": "Receiver Line Card Trouble",
            "description": "A line card identified by the passed address is in trouble",
            "concerns": "Line card number",
        },
        "YE": {
            "code": "YE",
            "type": "Receiver Line Card Restored",
            "description": "A line card identified by the passed address is restored",
            "concerns": "Line card number",
        },
        "YF": {
            "code": "YF",
            "type": "Parameter Checksum Fail",
            "description": "System data corrupted",
            "concerns": "Unused",
        },
        "YG": {
            "code": "YG",
            "type": "Parameter Changed",
            "description": "A TRANSMITTER’S parameters have been changed",
            "concerns": "Unused",
        },
        "YH": {
            "code": "YH",
            "type": "Bell Restored",
            "description": "A trouble condition has been restored on a Local Bell, Siren, or Annunciator",
            "concerns": "Unused",
        },
        "YI": {
            "code": "YI",
            "type": "Overcurrent Trouble",
            "description": "An Expansion Device has detected an overcurrent condition",
            "concerns": "Unused",
        },
        "YJ": {
            "code": "YJ",
            "type": "Overcurrent Restore",
            "description": "An Expansion Device has restored from an overcurrent condition",
            "concerns": "Unused",
        },
        "YK": {
            "code": "YK",
            "type": "Communications Restoral",
            "description": "TRANSMITTER has resumed communication with a RECEIVER",
            "concerns": "Unused",
        },
        "YM": {
            "code": "YM",
            "type": "System Battery Missing",
            "description": "TRANSMITTER/RECEIVER battery is missing",
            "concerns": "Unused",
        },
        "YN": {
            "code": "YN",
            "type": "Invalid Report",
            "description": "TRANSMITTER has sent a packet with invalid data",
            "concerns": "Unused",
        },
        "YO": {
            "code": "YO",
            "type": "Unknown Message",
            "description": "An unknown message was received from automation or the printer",
            "concerns": "Unused",
        },
        "YP": {
            "code": "YP",
            "type": "Power Supply Trouble",
            "description": "TRANSMITTER/RECEIVER has a problem with the power supply",
            "concerns": "Unused",
        },
        "YQ": {
            "code": "YQ",
            "type": "Power Supply Restored",
            "description": "TRANSMITTER’S/RECEIVER’S power supply has been restored",
            "concerns": "Unused",
        },
        "YR": {
            "code": "YR",
            "type": "System Battery Restoral",
            "description": "Low battery has been corrected",
            "concerns": "Unused",
        },
        "YS": {
            "code": "YS",
            "type": "Communications Trouble",
            "description": "RECEIVER and TRANSMITTER",
            "concerns": "Unused",
        },
        "YT": {
            "code": "YT",
            "type": "System Battery Trouble",
            "description": "Low battery in control/communicator",
            "concerns": "Unused",
        },
        "YU": {
            "code": "YU",
            "type": "Diagnostic Error",
            "description": "An expansion/peripheral device is reporting a diagnostic error",
            "concerns": "Condition number",
        },
        "YW": {
            "code": "YW",
            "type": "Watchdog Reset",
            "description": "The TRANSMITTER created an internal reset",
            "concerns": "Unused",
        },
        "YX": {
            "code": "YX",
            "type": "Service Required",
            "description": "A TRANSMITTER/RECEIVER needs service",
            "concerns": "Unused",
        },
        "YY": {
            "code": "YY",
            "type": "Status Report",
            "description": "This is a header for an account status report transmission",
            "concerns": "Unused",
        },
        "YZ": {
            "code": "YZ",
            "type": "Service Completed",
            "description": "Required TRANSMITTER / RECEIVER service completed",
            "concerns": "Mfr defined",
        },
        "ZA": {
            "code": "ZA",
            "type": "Freeze Alarm",
            "description": "Low temperature detected at premises",
            "concerns": "Zone or point",
        },
        "ZB": {
            "code": "ZB",
            "type": "Freeze Bypass",
            "description": "Low temperature detection has been bypassed",
            "concerns": "Zone or point",
        },
        "ZH": {
            "code": "ZH",
            "type": "Freeze Alarm Restore",
            "description": "Alarm condition eliminated",
            "concerns": "Zone or point",
        },
        "ZJ": {
            "code": "ZJ",
            "type": "Freeze Trouble Restore",
            "description": "Trouble condition eliminated",
            "concerns": "Zone or point",
        },
        "ZR": {
            "code": "ZR",
            "type": "Freeze Restoral",
            "description": "Alarm/trouble condition has been eliminated",
            "concerns": "Zone or point",
        },
        "ZS": {
            "code": "ZS",
            "type": "Freeze Supervisory",
            "description": "Unsafe freeze detection system condition",
            "concerns": "Zone or point",
        },
        "ZT": {
            "code": "ZT",
            "type": "Freeze Trouble",
            "description": "Zone disabled by fault",
            "concerns": "Zone or point",
        },
        "ZU": {
            "code": "ZU",
            "type": "Freeze Unbypass",
            "description": "Low temperature detection bypass removed",
            "concerns": "Zone or point",
        },
    }
