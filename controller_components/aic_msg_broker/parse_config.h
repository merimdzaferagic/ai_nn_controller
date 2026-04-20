#ifndef SCALE_RIC_DATABUS_H
#define SCALE_RIC_DATABUS_H

#include <algorithm>
#include <string.h>
#include <fstream>
#include <iostream>
#include <map>

std::map<std::string, std::string> read_config(std::string cfg_file_name);

#endif // SCALE_RIC_DATABUS_H