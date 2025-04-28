cmake_minimum_required(VERSION 3.13)

project(piper C CXX)

add_subdirectory(subprojects/pybind11)

find_package(PkgConfig)
pkg_check_modules(SPDLOG REQUIRED spdlog)

find_package(spdlog REQUIRED)
include_directories(${spdlog_INCLUDE_DIRS})

file(READ "${CMAKE_CURRENT_LIST_DIR}/../../VERSION" piper_version)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

ADD_EXECUTABLE(piper main.cpp piper.cpp)

string(APPEND CMAKE_CXX_FLAGS " -Wall -Wextra -Wl,-rpath,'$ORIGIN'")
string(APPEND CMAKE_C_FLAGS " -Wall -Wextra")

pybind11_add_module(piper src/piper.cpp)

set(PIPER_PHONEMIZE_ROOTDIR ${CMAKE_CURRENT_LIST_DIR}/../../lib/${CMAKE_HOST_SYSTEM_NAME}-${CMAKE_HOST_SYSTEM_PROCESSOR}/piper_phonemize)

target_link_libraries(piper
		      PRIVATE
                      piper_phonemize
                      espeak-ng
                      onnxruntime
                      pthread
                      ${SPDLOG_LIBRARIES})

if(NOT APPLE)
  target_link_libraries(piper -static-libgcc -static-libstdc++)
endif()

target_link_directories(piper PUBLIC
                        ${PIPER_PHONEMIZE_ROOTDIR}/lib)

target_include_directories(piper PRIVATE
			   ${CMAKE_CURRENT_SOURCE_DIR}/src
    		           ${CMAKE_CURRENT_SOURCE_DIR}/subprojects/piper-src/include
                           ${PIPER_PHONEMIZE_ROOTDIR}/include
                           ${SPDLOG_INCLUDE_DIRS})

target_compile_options(piper PUBLIC
                       ${SPDLOG_CFLAGS_OTHER})

target_compile_definitions(piper PUBLIC _PIPER_VERSION=${piper_version})

target_include_directories(piper PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
  $<INSTALL_INTERFACE:include>
  /app/include/piper-phonemize
)
install(TARGETS piper
    LIBRARY DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/python3.12/site-packages
)