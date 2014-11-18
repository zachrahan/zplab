// The MIT License (MIT)
// 
// Copyright (c) 2014 WUSTL ZPLAB
// 
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
// 
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
// 
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
// 
// Authors: Erik Hvatum <ice.rikh@gmail.com>

#include "LinearClassifier.h"

LinearClassifier::LinearClassifier(Py::PythonClassInstance *self, Py::Tuple &args, Py::Dict &kwds)
  : Py::PythonClass<LinearClassifier>::PythonClass(self, args, kwds),
    m_model(nullptr)
{
    std::cout << "LinearClassifier c'tor Called with " << args.length() << " normal arguments." << std::endl;
    Py::List names( kwds.keys() );
    std::cout << "and with " << names.length() << " keyword arguments:" << std::endl;
    for( Py::List::size_type i=0; i< names.length(); i++ )
    {
        Py::String name( names[i] );
        std::cout << "    " << name << std::endl;
    }
}

LinearClassifier::~LinearClassifier()
{
    std::cout << "~LinearClassifier" << std::endl;
}

void LinearClassifier::init_type()
{
    behaviors().name("LinearClassifier");
    behaviors().doc("Python wrapper class around C++ wrapper class around liblinear.");
    behaviors().supportGetattro();
    behaviors().supportSetattro();

    behaviors().readyType();
}

Py::Object LinearClassifier::getattro(const Py::String &name_)
{
    return genericGetAttro(name_);
}

int LinearClassifier::setattro(const Py::String &name_, const Py::Object &value)
{
    return genericSetAttro(name_, value);
}

