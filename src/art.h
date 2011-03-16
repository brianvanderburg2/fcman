// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_ART_H
#define __FCMAN_ART_H


// Requirements
#include <wx/defs.h>
#include <wx/iconbndl.h>


// Access art resources
class Art
{
public:
    static wxIconBundle GetMainIcons();
    static wxIcon GetFolderIcon();
    static wxIcon GetFileIcon();
    static wxIcon GetErrorIcon();
};

#endif // Header guard



