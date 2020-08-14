from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration
import os

class CorradeConan(ConanFile):
    name = "Corrade"
    version = "2020.06"
    description = "Corrade is a multiplatform utility library written in C++11/C++14."
    topics = ("conan", "corrade", "magnum", "filesystem", "console", "environment", "os", "data structures")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://magnum.graphics/corrade"
    author = "helmesjo <helmesjo@gmail.com>"
    license = "MIT"
    exports_sources = ["CMakeLists.txt"]
    generators = "cmake"
    short_paths = True
    _cmake = None

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_deprecated": [True, False],
        "with_interconnect": [True, False],
        "with_main": [True, False],
        "with_pluginmanager": [True, False],
        "with_testsuite": [True, False],
        "with_utility": [True, False],
        "with_rc": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_deprecated": False,
        "with_interconnect": True,
        "with_main": True,
        "with_pluginmanager": True,
        "with_testsuite": True,
        "with_utility": True,
        "with_rc": True,
    }

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.settings.compiler == "Visual Studio" and tools.Version(self.settings.compiler.version) < 14:
            raise ConanInvalidConfiguration("Corrade requires Visual Studio version 14 or greater")
        if tools.cross_building(self):
            self.output.warn("This Corrade recipe could not be prepared for cross building")

    def source(self):
        # Rename to "source_subfolder" is a convention to simplify later steps
        tools.get(**self.conan_data["sources"][self.version])
        os.rename("corrade-{}".format(self.version), self._source_subfolder)

    def _configure_cmake(self):
        if not self._cmake:
            self._cmake = CMake(self)
            def add_cmake_option(option, value):
                var_name = "{}".format(option).upper()
                value_str = "{}".format(value)
                var_value = "ON" if value_str == 'True' else "OFF" if value_str == 'False' else value_str 
                self._cmake.definitions[var_name] = var_value
                print("{0}={1}".format(var_name, var_value))

            for option, value in self.options.items():
                add_cmake_option(option, value)

            add_cmake_option("BUILD_STATIC", not self.options.shared)
            add_cmake_option("BUILD_STATIC_PIC", not self.options.shared and self.options.get_safe("fPIC") == True)

            if self.settings.compiler == "Visual Studio":
                self._cmake.definitions["MSVC2015_COMPATIBILITY"] = "ON" if self.settings.compiler.version == "14" else "OFF"
                self._cmake.definitions["MSVC2017_COMPATIBILITY"] = "ON" if self.settings.compiler.version == "15" else "OFF"
                self._cmake.definitions["MSVC2019_COMPATIBILITY"] = "ON" if self.settings.compiler.version == "16" else "OFF"

            # Corrade uses suffix on the resulting "lib"-folder when running cmake.install()
            # Set it explicitly to empty, else Corrade might set it implicitly (eg. to "64")
            self._cmake.definitions["LIB_SUFFIX"] = ""

            self._cmake.configure(build_folder=self._build_subfolder)

        return self._cmake

    def build(self):
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy("COPYING", dst="licenses", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install()

        share_cmake = os.path.join(self.package_folder, "share", "cmake", "Corrade")
        #self.copy("CMakeLists.txt", src=share_cmake, dst=os.path.join(self.package_folder, "lib", "cmake", "Corrade"))
        self.copy("CorradeConfig.cmake", src=share_cmake, dst=os.path.join(self.package_folder, "lib", "cmake", "Corrade"))
        self.copy("CorradeLibSuffix.cmake", src=share_cmake, dst=os.path.join(self.package_folder, "lib", "cmake", "Corrade"))
        self.copy("FindCorrade.cmake", src=share_cmake, dst=os.path.join(self.package_folder, "lib", "cmake", "Corrade"))
        self.copy("UseCorrade.cmake", src=share_cmake, dst=os.path.join(self.package_folder, "lib", "cmake", "Corrade"))
        tools.rmdir(os.path.join(self.package_folder, "share"))

    def package_info(self):
        suffix = "-d" if self.settings.build_type == "Debug" else ""
        builtLibs = tools.collect_libs(self)


        components = {
            "Containers": [],
            "Utility": ["Containers"],
            "Interconnect": ["Containers"],
            "PluginManager": ["Containers"],
            "TestSuite": ["Containers"],
            "Main": []
        }
        
        header_only = ["Containers"]
        
        for component, deps in components.items():
            lib = "Corrade" + component + suffix
            if lib in builtLibs or component in header_only:
                self.cpp_info.components[component].names["cmake_find_package"] = component
                self.cpp_info.components[component].names["cmake_find_package_multi"] = component
                if component not in header_only:
                    self.cpp_info.components[component].libs = [lib]
                self.cpp_info.components[component].requires = deps
                self.cpp_info.components[component].includedirs.append("include")
                if self.settings.os == "Linux":
                    self.cpp_info.components[component].system_libs = ["m", "dl"]
                    
                self.cpp_info.components[component].builddirs.append(os.path.join("lib", "cmake", "Corrade"))
                self.cpp_info.components[component].build_modules.append(os.path.join("lib", "cmake", "Corrade", "FindCorrade.cmake"))
                self.cpp_info.components[component].build_modules.append(os.path.join("lib", "cmake", "Corrade", "CorradeLibSuffix.cmake"))
                self.cpp_info.components[component].build_modules.append(os.path.join("lib", "cmake", "Corrade", "CMakeLists.txt"))
                self.cpp_info.components[component].build_modules.append(os.path.join("lib", "cmake", "Corrade", "CorradeConfig.cmake"))
                self.cpp_info.components[component].build_modules.append(os.path.join("lib", "cmake", "Corrade", "UseCorrade.cmake"))    

        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
        if self.options.shared:
            # Help linker find rpaths
            if self.settings.os == "Linux":
                self.env_info.LD_LIBRARY_PATH.append(os.path.join(self.package_folder, "lib"))
            if self.settings.os == "Macos":
                self.env_info.DYLD_LIBRARY_PATH.append(os.path.join(self.package_folder, "lib"))
