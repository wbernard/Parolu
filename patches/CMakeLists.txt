cmake_minimum_required(VERSION 3.10)

project(piper_api C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(PIPER_PHONEMIZE_INCLUDE ${CMAKE_INCLUDE_PATH}/piper-phonemize CACHE STRING "")

set(CMAKE_POSITION_INDEPENDENT_CODE ON)

add_library(piper_api STATIC piper_api.cpp src/cpp/piper.cpp)

find_package(PkgConfig REQUIRED)
pkg_check_modules(ESPEAK_NG REQUIRED espeak-ng<2)

find_library(onnxruntime_path onnxruntime REQUIRED)

target_link_libraries(piper_api
  ${onnxruntime_path}
  pthread
  ${ESPEAK_NG_LIBRARIES})

target_link_directories(piper_api PUBLIC
  ${ESPEAK_NG_LIBRARY_DIRS}
  ${CMAKE_LIBRARY_PATH})

target_include_directories(piper_api PUBLIC
  ${ESPEAK_NG_INCLUDE_DIRS}
  ${PIPER_PHONEMIZE_INCLUDE}
  src/cpp)

target_compile_options(piper_api PUBLIC
  ${ESPEAK_NG_CFLAGS_OTHER})

set_target_properties(piper_api PROPERTIES PUBLIC_HEADER "piper_api.h")

install(TARGETS piper_api
    LIBRARY DESTINATION ${CMAKE_INSTALL_PREFIX}/lib
    ARCHIVE DESTINATION ${CMAKE_INSTALL_PREFIX}/lib
    PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_PREFIX}/include
)
