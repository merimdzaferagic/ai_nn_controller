#include "parse_config.h"

std::map<std::string, std::string> read_config(std::string cfg_file_name) {
    // std::ifstream is RAII, i.e. no need to call close
    std::ifstream cFile(cfg_file_name);
    std::map<std::string, std::string> config;
    if (cFile.is_open()) {
        std::string line;
        while (getline(cFile, line)) {
            line.erase(std::remove_if(line.begin(), line.end(), isspace),
                       line.end());
            if (line[0] == '#' || line.empty()) continue;
            auto delimiterPos = line.find("=");
            auto name = line.substr(0, delimiterPos);
            auto value = line.substr(delimiterPos + 1);
            config[name] = value;
            std::cout << name << " " << value << '\n';
        }
    } else {
        std::cerr << "Couldn't open config file for reading.\n";
    }
    return config;
}
