// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_TREECTRL_H
#define __FCMAN_TREECTRL_H


// Requirements
#include <wx/defs.h>
#include <wx/treectrl.h>


// Tree item data class
template <typename T>
class TreeItemData : public wxTreeItemData
{
public:
    TreeItemData(T* data) : m_data(data)
    {
    }

    template <typename U>
    TreeItemData(U* data) : m_data(data)
    {
    }

    template <typename U>
    void SetData(U* data) { m_data = data; }

    T* GetData() const { return m_data; }

private:
    T* m_data;
};

// Tree control class
template <typename T>
class TreeCtrl : public wxTreeCtrl
{
public:
    TreeCtrl(wxWindow* parent, wxWindowID id, long style) :
        wxTreeCtrl(parent, id, wxDefaultPosition, wxDefaultSize, style)
    {
    }

    template <typename U>
    void SetItemData(const wxTreeItemId& id, U* data)
    {
        TreeItemData<T>* itemdata = new TreeItemData<T>(data);
        wxTreeCtrl::SetItemData(id, itemdata);
    }

    T* GetItemData(const wxTreeItemId& id)
    {
        // It is assumed that HasItemData returns true
        wxTreeItemData* data = wxTreeCtrl::GetItemData(id);
        if(!data)
            return NULL;

        TreeItemData<T>* itemdata = dynamic_cast<TreeItemData<T>*>(data);
        if(!itemdata)
            return NULL;

        return itemdata->GetData();
    }
};


#endif // Header guard



