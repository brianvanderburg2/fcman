// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_LISTBOX_H
#define __FCMAN_LISTBOX_H


// Requirements
#include <wx/defs.h>
#include <wx/listbox.h>


// List box class
template <typename T>
class ListBox : public wxListBox
{
public:
    ListBox(wxWindow* parent, wxWindowID id, long style) :
        wxListBox(parent, id, wxDefaultPosition, wxDefaultSize, 0, NULL, style)
    {
    }

    template <typename U>
    void SetItemData(unsigned int index, U* data)
    {
        T* itemdata = data;
        wxListBox::SetClientData(index, reinterpret_cast<void*>(itemdata));
    }

    T* GetItemData(unsigned int index)
    {
        return reinterpret_cast<T*>(wxListBox::GetClientData(index));
    }
};


#endif // Header guard



