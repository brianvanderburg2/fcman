// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_COLLECTION_VERSION_H
#define __FCMAN_COLLECTION_VERSION_H


// Requirements
#include <wx/defs.h>
#include <wx/dynarray.h>
#include <wx/string.h>


// Version object
class Version
{
public:
    // ctor/dtor (default copy and assignment are fine)
    Version();
    ~Version();

    // Information
    void Set(const wxString& version);
    const wxString& Get() const { return m_version; }
    int Compare(const Version& other) const;

    bool IsOk() const;

protected:
    static int PartValue(const wxString& part);

    wxString m_version;
    wxArrayInt m_parts;
};



#endif // Header guard



