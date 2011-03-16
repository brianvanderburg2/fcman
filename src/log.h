// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_LOG_H
#define __FCMAN_LOG_H


// Requirements
#include <wx/defs.h>
#include <wx/textctrl.h>


// Log control class
class Log : public wxTextCtrl
{
public:
    // ctor
    Log(wxWindow* parent, wxWindowID id);

    // Actions
    void Clear();
    void LogMessage(const wxString& message, bool important = false);
};


#endif // Header guard



