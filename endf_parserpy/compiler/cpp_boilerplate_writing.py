############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/18
# Last modified:   2024/05/18
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


from . import cpp_primivites as cpp


def module_header_writing():
    code = r"""

    std::string float2endfstr(double value) {
      std::ostringstream oss;
      oss << std::scientific << std::setprecision(6);
      oss << std::setw(11) << value;
      return oss.str();
    }


    std::string int2endfstr(int value) {
      std::ostringstream oss;
      oss << std::right << std::setw(11) << value;
      return oss.str();
    }


    template<typename T>
    void cpp_write_field(std::string& line, const char fieldnum, T value) {
      static_assert(std::is_same<T, double>::value || std::is_same<T, int>::value, "T must be int or double");
      std::string fieldstr;
      if (std::is_same<T, double>::value) {
        fieldstr = float2endfstr(value);
      } else {
        fieldstr = int2endfstr(value);
      }
      line.replace(fieldnum*11, 11, fieldstr);
    }
    """
    return cpp.indent_code(code, -4)
