// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_OPTIONS_H
#define __FCMAN_OPTIONS_H


// Requirements
#include "config.h"

#include <wx/defs.h>

class WXDLLIMPEXP_BASE wxConfigBase;


// Options
class Options
{
public:
    // ctor/dtor
    Options();
    ~Options();

    // Load/save
    void Load(wxConfigBase* config);
    void Save(wxConfigBase* config) const;

};



#endif // Header guard



