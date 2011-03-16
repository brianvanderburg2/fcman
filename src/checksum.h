// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_CHECKSUM_H
#define __FCMAN_CHECKSUM_H


// Requirements
#include <wx/defs.h>
#include <wx/arrstr.h>
#include <wx/string.h>


// Checksum calculator class
class ChecksumCalculator
{
public:
    // Does a certain type exist
    static bool Exists(const wxString& type);

    // Enumerate available types
    static wxArrayString GetTypes();

    // Ctor/dtor
    ChecksumCalculator(const wxString& type);
    ~ChecksumCalculator();

    // Is it valud
    bool IsOk() const { return m_impl != NULL; }

    // Update the checksum
    void Update(void* data, size_t len);

    // Get the checksum string in the form type:value
    wxString Finish();

private:
    struct Impl;
    Impl* m_impl;
};



#endif // Header guard



