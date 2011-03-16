// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_LISTCTRL_H
#define __FCMAN_LISTCTRL_H


// Requirements
#include <wx/defs.h>
#include <wx/listctrl.h>


// List control class
template <typename T>
class ListCtrl : public wxListView
{
public:
    ListCtrl(wxWindow* parent, wxWindowID id, long style)
    {
        Create(parent, id, wxDefaultPosition, wxDefaultSize, style);
    }

    template <typename U>
    void SetItemData(long index, U* data)
    {
        T* itemdata = data;
        wxListView::SetItemPtrData(index, reinterpret_cast<wxUIntPtr>(itemdata));
    }

    T* GetItemData(long index)
    {
        return reinterpret_cast<T*>(wxListView::GetItemData(index));
    }
};


#endif // Header guard



